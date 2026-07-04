from __future__ import annotations

from app.features.engineering import FeatureEngineeringService
from app.features.snapshot_store import SnapshotStore

# Documented, transparent elasticities (NOT a trained model — a clearly-labeled
# projection formula, per CLAUDE.md 5B item 1). Each maps a lever to a driver.
ELASTICITY = {
    # +1% meetings -> extra fraction of the weighted CRM pipeline that converts.
    "meeting_to_conversion": 0.50,
    # +1% prospecting -> +this fraction of annualized NNM (new-money inflow).
    "prospecting_to_nnm": 0.60,
    # fee yield applied to net-new AUM to estimate incremental advisory revenue.
    "aum_fee_yield": 0.0085,
    # each extra goal review -> +this many points of goal attainment.
    "review_to_goal_points": 3.0,
    # +1% meetings -> +this many points of goal attainment (engagement effect).
    "meeting_to_goal_points": 0.10,
}


class WhatIfService:
    """Scenario projection over an advisor's REAL current feature snapshot.
    Baselines are the advisor's actual values; levers apply documented
    elasticities prorated to the horizon. Every projected metric returns its
    baseline, the formula and the assumptions — no fabricated numbers."""

    def _snapshot(self, advisor_id: str) -> dict:
        snap = SnapshotStore().latest_for_entity("ADVISOR", advisor_id)
        if snap is None:
            snap = FeatureEngineeringService().compute_advisor_snapshot(advisor_id)
        return snap

    def simulate(
        self,
        advisor_id: str,
        meeting_increase_pct: float = 0.0,
        prospecting_increase_pct: float = 0.0,
        aum_growth_pct: float = 0.0,
        goal_reviews_added: float = 0.0,
        horizon_months: int = 6,
    ) -> dict:
        snap = self._snapshot(advisor_id)
        f = snap["features"]

        def num(key: str, default: float = 0.0) -> float:
            v = f.get(key)
            return float(v) if v is not None else default

        revenue_ltm = num("revenue_ltm")
        nnm_3m = num("nnm_3m")
        aum_total = num("aum_total")
        weighted_pipeline = num("weighted_pipeline_value")
        kpi_on_track = num("kpi_on_track_ratio")
        managed_ratio = num("managed_revenue_ratio")

        horizon_frac = max(0.0, horizon_months) / 12.0
        nnm_annual = nnm_3m * 4.0
        goal_attainment_now = round(kpi_on_track * 100.0, 1)

        # --- Revenue: extra converted pipeline from more client meetings ---
        extra_conversion = (meeting_increase_pct / 100.0) * ELASTICITY["meeting_to_conversion"]
        extra_conversion = min(extra_conversion, 0.5)  # cap: can't convert >50% more
        pipeline_revenue_gain = weighted_pipeline * extra_conversion * horizon_frac
        # AUM fee revenue from net-new money over the horizon (see AUM block)
        nnm_gain = nnm_annual * (prospecting_increase_pct / 100.0) * ELASTICITY["prospecting_to_nnm"] * horizon_frac
        net_new_aum = aum_total * (aum_growth_pct / 100.0) * horizon_frac + nnm_gain
        fee_revenue_gain = net_new_aum * ELASTICITY["aum_fee_yield"]
        revenue_proj = revenue_ltm + pipeline_revenue_gain + fee_revenue_gain

        # --- Managed revenue (uses real managed ratio on the projected revenue) ---
        managed_now = revenue_ltm * managed_ratio
        managed_proj = revenue_proj * managed_ratio

        # --- NNM ---
        nnm_now = nnm_annual
        nnm_proj = nnm_annual + nnm_gain

        # --- AUM ---
        aum_proj = aum_total + net_new_aum

        # --- Goal attainment ---
        goal_gain = (
            goal_reviews_added * ELASTICITY["review_to_goal_points"]
            + meeting_increase_pct * ELASTICITY["meeting_to_goal_points"]
        ) * min(1.0, horizon_frac + 0.5)
        goal_proj = min(100.0, goal_attainment_now + goal_gain)

        def metric(name: str, current: float, projected: float, unit: str, formula: str) -> dict:
            change = projected - current
            return {
                "metric": name,
                "unit": unit,
                "current": round(current, 2),
                "projected": round(projected, 2),
                "change": round(change, 2),
                "change_pct": round((change / current * 100.0), 2) if current else None,
                "formula": formula,
            }

        metrics = [
            metric("Total Revenue", revenue_ltm, revenue_proj, "USD",
                   f"revenue_ltm + weighted_pipeline({weighted_pipeline:.0f})×extra_conversion"
                   f"({extra_conversion:.3f})×horizon({horizon_frac:.2f}) + fee_revenue({fee_revenue_gain:.0f})"),
            metric("Managed Revenue", managed_now, managed_proj, "USD",
                   f"projected_revenue × managed_ratio({managed_ratio:.4f})"),
            metric("NNM (annualized)", nnm_now, nnm_proj, "USD",
                   f"nnm_3m×4 + nnm_annual×prospecting({prospecting_increase_pct:.0f}%)×"
                   f"{ELASTICITY['prospecting_to_nnm']}×horizon({horizon_frac:.2f})"),
            metric("AUM", aum_total, aum_proj, "USD",
                   f"aum_total + aum×growth({aum_growth_pct:.0f}%)×horizon + nnm_gain({nnm_gain:.0f})"),
            metric("Goal Attainment", goal_attainment_now, goal_proj, "pts",
                   f"kpi_on_track×100 + reviews({goal_reviews_added:.0f})×"
                   f"{ELASTICITY['review_to_goal_points']} + meetings×{ELASTICITY['meeting_to_goal_points']}"),
        ]

        return {
            "advisor_id": advisor_id,
            "snapshot_id": snap.get("snapshot_id"),
            "horizon_months": horizon_months,
            "levers": {
                "meeting_increase_pct": meeting_increase_pct,
                "prospecting_increase_pct": prospecting_increase_pct,
                "aum_growth_pct": aum_growth_pct,
                "goal_reviews_added": goal_reviews_added,
            },
            "baseline_features": {
                "revenue_ltm": revenue_ltm, "nnm_3m": nnm_3m, "aum_total": aum_total,
                "weighted_pipeline_value": weighted_pipeline, "kpi_on_track_ratio": kpi_on_track,
                "managed_revenue_ratio": managed_ratio,
            },
            "metrics": metrics,
            "elasticities": ELASTICITY,
            "note": (
                "Projection uses the advisor's REAL current feature snapshot as the baseline and "
                "applies documented elasticities prorated to the horizon — a transparent formula, "
                "not a trained model and not fabricated figures."
            ),
        }
