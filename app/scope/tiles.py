from __future__ import annotations

"""Scope-aware KPI tile sets for the Executive Dashboard (REQ-1).

The mockup's tiles are: colored icon + bold value + green/red delta + a "vs PY: $X"
prior line. Crucially the tile SET adapts to the selected scope — an advisor sees
their own book (revenue, managed %, households, revenue/household, AGP risk,
pipeline), a leader sees rollups. Never "Advisors In Scope: 1" at advisor scope.

Every tile value is a real computed figure and carries a `trace` (REQ-2): the
source computation and a link to the screen where the underlying model/lineage
lives. Deltas/priors are only emitted where a REAL prior-window figure exists —
never fabricated.
"""


def _tile(tid: str, label: str, value: float | int | None, unit: str, icon: str,
          *, delta_pct: float | None = None, prior: float | None = None,
          prior_label: str = "vs PY", positive_is_good: bool = True,
          trace_source: str = "", trace_computation: str = "", trace_link: str | None = None,
          delta_unit: str = "pct") -> dict:
    return {
        "id": tid,
        "label": label,
        "value": value,
        "unit": unit,               # usd | pct | count | score
        "icon": icon,               # frontend icon key
        "delta_pct": delta_pct,     # signed; None = no honest prior exists
        "delta_unit": delta_unit,   # pct | pp
        "prior": prior,             # prior-window absolute value for the "vs PY: $X" line
        "prior_label": prior_label,
        "positive_is_good": positive_is_good,
        "trace": {
            "source": trace_source,
            "computation": trace_computation,
            "link": trace_link,
        },
    }


def _pct_delta(cur: float, prior: float | None) -> float | None:
    if prior is None or prior == 0:
        return None
    return round((cur - prior) / prior * 100.0, 1)


def _driver_row(revenue: dict, category: str) -> dict | None:
    for r in revenue.get("revenue_drivers", []):
        if r.get("category") == category:
            return r
    return None


def advisor_tiles(features: dict, revenue: dict, headline: dict) -> list[dict]:
    """The advisor-persona tile set (mockup left-to-right: Total Revenue, Managed
    Revenue, Managed Revenue %, Households, Revenue/Household — plus AGP Risk and
    Weighted Pipeline per the brief)."""
    total = float(headline.get("revenue") or 0.0)
    prior_total = headline.get("prior")
    period = revenue.get("kpis", {}).get("period", "LTM")

    # Managed Accounts revenue in the SAME period window, with its real prior-year value
    # from the YoY driver rows (only present when the prior window is fully covered).
    managed_cur = next((b["revenue"] for b in revenue.get("by_business_line", [])
                        if b["category"] == "Managed Accounts"), 0.0)
    md = _driver_row(revenue, "Managed Accounts")
    managed_prior = md.get("prior_revenue") if md else None

    managed_pct = round(managed_cur / total * 100.0, 1) if total else None
    managed_pct_prior = (
        round(managed_prior / prior_total * 100.0, 1)
        if (managed_prior is not None and prior_total) else None
    )

    hh = features.get("household_count")
    hh_count = int(hh) if hh is not None else None
    rev_per_hh = round(total / hh_count, 0) if (total and hh_count) else None
    rev_per_hh_prior = round(float(prior_total) / hh_count, 0) if (prior_total and hh_count) else None

    risk = features.get("agp_risk_score")
    pipeline = features.get("weighted_pipeline_value")
    aum = features.get("aum_total")
    nnm_ann = (float(features.get("nnm_3m")) * 4.0) if features.get("nnm_3m") is not None else None

    snap_src = "latest advisor feature snapshot (Feature Engineering pipeline, Phase 5 lineage)"
    tx_src = "Σ phx_dm_revenue_transaction via transaction_for_advisor edges, period-windowed"

    return [
        _tile("total_revenue", f"Total Revenue ({period})", round(total, 2), "usd", "dollar",
              delta_pct=headline.get("delta_pct"), prior=prior_total,
              trace_source=tx_src,
              trace_computation="Σ revenue_amount in the selected window; delta vs the real month-shifted −12 window",
              trace_link="/revenue-analytics"),
        _tile("managed_revenue", f"Managed Revenue ({period})", round(managed_cur, 2), "usd", "layers",
              delta_pct=_pct_delta(managed_cur, managed_prior), prior=managed_prior,
              trace_source=tx_src + " → product→category = Managed Accounts",
              trace_computation="Σ revenue_amount of transactions whose product maps to the Managed Accounts category",
              trace_link="/revenue-analytics"),
        _tile("managed_pct", "Managed Revenue %", managed_pct, "pct", "pie",
              delta_pct=(round(managed_pct - managed_pct_prior, 1)
                         if (managed_pct is not None and managed_pct_prior is not None) else None),
              delta_unit="pp", prior=managed_pct_prior,
              trace_source=tx_src,
              trace_computation="Managed Accounts revenue ÷ total revenue, same window; delta in percentage points",
              trace_link="/revenue-analytics"),
        _tile("households", "Households", hh_count, "count", "users",
              trace_source=snap_src,
              trace_computation="household_count feature = count of advisor_serves_household edges (graph traversal)",
              trace_link="/advisor-360"),
        _tile("rev_per_household", "Revenue / Household", rev_per_hh, "usd", "chart",
              delta_pct=_pct_delta(rev_per_hh or 0.0, rev_per_hh_prior), prior=rev_per_hh_prior,
              trace_source=tx_src,
              trace_computation="period revenue ÷ current household_count (prior line uses the real prior-window revenue)",
              trace_link="/advisor-360"),
        _tile("aum", "AUM", aum, "usd", "wallet",
              trace_source=snap_src,
              trace_computation="aum_total feature = Σ account AUM across the advisor's households",
              trace_link="/advisor-360"),
        _tile("agp_risk", "AGP Risk Score", risk, "score", "shield", positive_is_good=False,
              trace_source="AGP off-track prediction model (real model tier, feature contributions + confidence)",
              trace_computation="agp_risk_score — open the Predictions page for the model's per-feature contributions",
              trace_link="/predictions"),
        _tile("pipeline", "Weighted Pipeline", pipeline, "usd", "target",
              trace_source=snap_src + " ← CRM opportunities",
              trace_computation="Σ open CRM opportunity amount × stage probability (weighted_pipeline_value feature)",
              trace_link="/crm"),
    ] + ([
        _tile("nnm", "NNM (Annualized)", round(nnm_ann, 2), "usd", "piggy",
              trace_source=snap_src,
              trace_computation="nnm_3m × 4 (annualized net new money)",
              trace_link="/revenue-analytics"),
    ] if nnm_ann is not None else [])


def leadership_tiles(totals: dict, revenue: dict, headline: dict, comparison: dict) -> list[dict]:
    """Rollup tile set for Firm/Division/Region/Market scopes."""
    period = revenue.get("kpis", {}).get("period", "LTM")
    status = totals.get("status_distribution", {})
    at_risk = status.get("attention", 0) + status.get("urgent", 0) + status.get("critical", 0)

    managed_cur = next((b["revenue"] for b in revenue.get("by_business_line", [])
                        if b["category"] == "Managed Accounts"), 0.0)
    md = _driver_row(revenue, "Managed Accounts")
    managed_prior = md.get("prior_revenue") if md else None

    roll_src = "Σ/mean over every in-scope advisor's real feature snapshot (ScopeRollupService)"
    tx_src = "Σ phx_dm_revenue_transaction across in-scope advisors, period-windowed"

    return [
        _tile("total_revenue", f"Total Revenue ({period})", round(float(headline.get("revenue") or 0.0), 2),
              "usd", "dollar", delta_pct=headline.get("delta_pct"), prior=headline.get("prior"),
              trace_source=tx_src,
              trace_computation="Σ revenue_amount in the selected window; delta per the Compare-To control",
              trace_link="/revenue-analytics"),
        _tile("managed_revenue", f"Managed Revenue ({period})", round(managed_cur, 2), "usd", "layers",
              delta_pct=_pct_delta(managed_cur, managed_prior), prior=managed_prior,
              trace_source=tx_src + " → Managed Accounts category",
              trace_computation="Σ revenue of transactions whose product maps to Managed Accounts",
              trace_link="/revenue-analytics"),
        _tile("aum", "AUM", totals.get("aum_total"), "usd", "wallet",
              trace_source=roll_src,
              trace_computation="Σ aum_total over in-scope advisor snapshots",
              trace_link="/revenue-analytics"),
        _tile("nnm", "NNM (Annualized)", totals.get("nnm_annualized"), "usd", "piggy",
              trace_source=roll_src,
              trace_computation="Σ nnm_3m × 4 over in-scope advisors",
              trace_link="/revenue-analytics"),
        _tile("advisors", "Advisors In Scope", totals.get("advisor_count"), "count", "users",
              trace_source="hierarchy traversal (firm→division→region→market→advisor edges)",
              trace_computation="count of advisors resolved under the selected scope",
              trace_link="/hierarchy"),
        _tile("goal", "Avg Goal Attainment", totals.get("avg_goal_attainment"), "pct", "gauge",
              trace_source=roll_src,
              trace_computation="mean(kpi_on_track_ratio × 100) over in-scope advisors",
              trace_link="/agp"),
        _tile("agp_risk", "Avg AGP Risk", totals.get("avg_agp_risk_score"), "score", "shield",
              positive_is_good=False,
              trace_source="AGP off-track prediction model, averaged over in-scope advisors",
              trace_computation="mean(agp_risk_score); per-advisor model contributions on the Predictions page",
              trace_link="/predictions"),
        _tile("at_risk", "At-Risk Advisors", at_risk, "count", "alert", positive_is_good=False,
              trace_source="AGP-004 severity bands over each advisor's agp_risk_score",
              trace_computation="count of advisors banded attention/urgent/critical (<40 on-track, <70 attention, <85 urgent, ≥85 critical)",
              trace_link="/agp"),
    ]
