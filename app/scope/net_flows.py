"""AUM net-flows waterfall (bridge) — the classic executive wealth-management chart.

Reconciles Beginning AUM → Ending AUM over the period for any hierarchy scope, using only
real values from the foundation data:

    Beginning AUM
      + New AUM (inflows)         Σ positive monthly NNM over the window
      − Departures (outflows)     Σ negative monthly NNM over the window
      + Market / Organic Growth   reconciling residual (appreciation net of known flows)
      − Fees                      Σ FEE-type revenue transactions over the window
      = Ending AUM

Every explicit component is a real sum over the in-scope advisors' monthly AUM/NNM snapshots
and FEE transactions. Market/organic growth is the single reconciling residual so the bridge
lands exactly on the real Ending-AUM snapshot — labelled as such, never presented as a measured
input. Scope-aware via the same `resolve_scope_advisor_ids` the rest of the rollup uses.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config.settings import get_settings
from app.graph.foundation_store import get_foundation_store
from app.graph.queries.common import resolve_scope_advisor_ids

# Period → number of trailing months in the window.
_PERIOD_MONTHS = {"LTM": 12, "YTD": 12, "QTD": 3, "MTD": 1}


def _sample_dir() -> Path:
    return Path(get_settings().foundation_dir) / "data" / "sample"


@lru_cache(maxsize=1)
def _monthly() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(aum, nnm, fees) frames keyed by advisor_id + month_end. Cached."""
    d = _sample_dir()
    v, e = d / "vertices", d / "edges"

    aum = pd.read_csv(v / "phx_dm_monthly_aum.csv")
    aum = aum.merge(
        pd.read_csv(e / "phx_dm_aum_for_advisor.csv").rename(columns={"from_id": "aum_id", "to_id": "advisor_id"}),
        on="aum_id",
    )
    aum["month_end"] = pd.to_datetime(aum["month_end"])

    nnm = pd.read_csv(v / "phx_dm_monthly_nnm.csv")
    nnm = nnm.merge(
        pd.read_csv(e / "phx_dm_nnm_for_advisor.csv").rename(columns={"from_id": "nnm_id", "to_id": "advisor_id"}),
        on="nnm_id",
    )
    nnm["month_end"] = pd.to_datetime(nnm["month_end"])

    tx = pd.read_csv(v / "phx_dm_revenue_transaction.csv")
    tx = tx[tx["transaction_type"] == "FEE"].copy()
    tx = tx.merge(
        pd.read_csv(e / "phx_dm_transaction_for_advisor.csv").rename(columns={"from_id": "transaction_id", "to_id": "advisor_id"}),
        on="transaction_id",
    )
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
    return aum, nnm, tx


class AumNetFlowsService:
    def __init__(self) -> None:
        self._store = get_foundation_store()

    def waterfall(self, scope_type: str = "FIRM", scope_id: str = "F001", period: str = "LTM") -> dict:
        advisor_ids = set(resolve_scope_advisor_ids(self._store, scope_type.upper(), scope_id))
        aum, nnm, fees = _monthly()
        months = _PERIOD_MONTHS.get((period or "LTM").upper(), 12)

        aum_s = aum[aum["advisor_id"].isin(advisor_ids)]
        nnm_s = nnm[nnm["advisor_id"].isin(advisor_ids)]
        fee_s = fees[fees["advisor_id"].isin(advisor_ids)]
        if aum_s.empty:
            return {"available": False, "scope_type": scope_type, "scope_id": scope_id}

        all_months = sorted(aum_s["month_end"].unique())
        end_m = all_months[-1]
        begin_idx = max(0, len(all_months) - 1 - months)
        begin_m = all_months[begin_idx]
        window = all_months[begin_idx + 1:]  # months contributing flow AFTER the beginning snapshot

        beginning = float(aum_s.loc[aum_s["month_end"] == begin_m, "aum_amount"].sum())
        ending = float(aum_s.loc[aum_s["month_end"] == end_m, "aum_amount"].sum())

        flow = nnm_s[nnm_s["month_end"].isin(window)]
        inflows = float(flow.loc[flow["nnm_amount"] > 0, "nnm_amount"].sum())
        outflows = float(flow.loc[flow["nnm_amount"] < 0, "nnm_amount"].sum())  # negative

        fee_total = float(
            fee_s.loc[(fee_s["transaction_date"] > begin_m) & (fee_s["transaction_date"] <= end_m), "revenue_amount"].sum()
        )
        # Reconciling residual: everything the explicit flows don't explain is market/organic growth.
        growth = ending - beginning - (inflows + outflows) + fee_total

        steps = [
            {"label": "Beginning AUM", "kind": "base", "value": round(beginning)},
            {"label": "New AUM (Inflows)", "kind": "increase", "value": round(inflows)},
            {"label": "Departures (Outflows)", "kind": "decrease", "value": round(outflows)},
            {"label": "Market / Organic Growth", "kind": "residual", "value": round(growth)},
            {"label": "Fees", "kind": "decrease", "value": -round(fee_total)},
            {"label": "Ending AUM", "kind": "total", "value": round(ending)},
        ]
        return {
            "available": True,
            "scope_type": scope_type.upper(),
            "scope_id": scope_id,
            "period": (period or "LTM").upper(),
            "advisor_count": len(advisor_ids),
            "window": {"beginning_month": str(pd.Timestamp(begin_m).date()),
                       "ending_month": str(pd.Timestamp(end_m).date()), "months": len(window)},
            "beginning_aum": round(beginning),
            "ending_aum": round(ending),
            "net_change": round(ending - beginning),
            "components": {
                "inflows": round(inflows),
                "outflows": round(outflows),
                "organic_growth": round(growth),
                "fees": -round(fee_total),
            },
            "steps": steps,
            "note": (
                "Beginning/Ending AUM, inflows/outflows (signed monthly NNM) and Fees (FEE-type "
                "transactions) are real sums over in-scope advisors; Market/Organic Growth is the "
                "reconciling residual so the bridge lands on the real Ending-AUM snapshot."
            ),
        }
