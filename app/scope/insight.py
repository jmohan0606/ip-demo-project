from __future__ import annotations

from app.llm.client import get_llm_client, LLMClientError
from app.scope.dashboard import ScopeDashboardService


def _usd(v: float | None) -> str:
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if a >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if a >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


class ScopeInsightService:
    """Scope-level AI Insight Summary (Key Drivers / Watch Outs / What to Monitor)
    for the Executive Dashboard (12.1). Every driver/watch-out is DERIVED FROM the
    real ScopeDashboardService numbers for the *currently filtered scope + period*
    — the LLM writes only the executive-summary narrative, grounded in those same
    numbers, so the card is real even in mock mode and genuinely reasoned under
    LLM_CLIENT_MODE=claude. The AI Coaching Card is only meaningful at Advisor
    scope, so it is returned there only (client rule 12.1)."""

    def insight(self, scope_type: str, scope_id: str, period: str = "LTM",
                compare_to: str = "Prior Year", persona: str = "Advisor") -> dict:
        d = ScopeDashboardService().dashboard(scope_type, scope_id, period=period, compare_to=compare_to)
        t = d["totals"]
        head = d["headline"]
        status = t["status_distribution"]
        at_risk = status["attention"] + status["urgent"] + status["critical"]

        # ---- Key Drivers: the concrete figures that define this scope's picture.
        key_drivers = [
            {"label": f"Revenue ({d['period']})", "value": _usd(head.get("revenue")),
             "detail": f"{head.get('compare_to')} Δ {head.get('delta_pct')}%" if head.get("delta_pct") is not None else "current period"},
            {"label": "AUM", "value": _usd(t["aum_total"]), "detail": f"{t['advisor_count']} advisors in scope"},
            {"label": "NNM (Annualized)", "value": _usd(t["nnm_annualized"]), "detail": "Σ nnm_3m × 4"},
            {"label": "Avg Goal Attainment", "value": f"{t['avg_goal_attainment']}%", "detail": "mean KPI on-track ratio"},
            {"label": "Avg AGP Risk", "value": t["avg_agp_risk_score"], "detail": f"{at_risk} advisors need attention"},
        ]

        # ---- Watch Outs: real negatives ranked worst-first.
        watch_outs: list[dict] = []
        if status["critical"]:
            watch_outs.append({"title": f"{status['critical']} advisor(s) at CRITICAL AGP risk",
                               "summary": "Off-track on the AGP-004 risk band (score ≥ 85). Prioritize coaching.",
                               "severity": "High", "confidence": 0.9})
        if status["urgent"]:
            watch_outs.append({"title": f"{status['urgent']} advisor(s) URGENT",
                               "summary": "Risk band 70–84 — intervene before they slip to critical.",
                               "severity": "High", "confidence": 0.85})
        # Declining revenue drivers (business lines down YoY)
        for drv in d["revenue"].get("revenue_drivers", [])[:6]:
            if drv.get("change", 0) < 0:
                watch_outs.append({
                    "title": f"{drv['category']} revenue down {drv.get('change_pct')}% YoY",
                    "summary": f"{_usd(drv['revenue'])} vs {_usd(drv['prior_revenue'])} prior year — a {_usd(drv['change'])} drag.",
                    "severity": "Medium", "confidence": 0.8,
                })
        # Bottom markets
        bottom_mkts = d["markets"].get("bottom", [])
        if bottom_mkts:
            m = bottom_mkts[0]
            watch_outs.append({"title": f"Lowest market: {m['label']}",
                               "summary": f"{_usd(m['revenue_ltm'])} LTM across {m['advisor_count']} advisors ({_usd(m['rev_per_advisor'])}/advisor).",
                               "severity": "Medium", "confidence": 0.75})
        watch_outs = watch_outs[:4]

        what_to_monitor = [f"Revenue ({d['period']})", "AUM", "NNM", "Goal Attainment", "AGP Risk", "Managed Revenue"]

        # ---- Narrative: LLM writes the executive summary from the real numbers only.
        bench = d["benchmark"]
        top_adv = d["top_advisors"][:2]
        bot_adv = d["bottom_advisors"][:2]
        facts = (
            f"Scope: {d['scope_type']} {d['scope_id']} ({t['advisor_count']} advisors). "
            f"Revenue {d['period']} {_usd(head.get('revenue'))} ({head.get('compare_to')} Δ {head.get('delta_pct')}%). "
            f"AUM {_usd(t['aum_total'])}, NNM annualized {_usd(t['nnm_annualized'])}, "
            f"avg goal attainment {t['avg_goal_attainment']}%, avg AGP risk {t['avg_agp_risk_score']}, {at_risk} at-risk. "
            f"Revenue/advisor {_usd(bench.get('current_per_advisor'))} vs firm avg {_usd(bench.get('firm_per_advisor'))} "
            f"({bench.get('vs_firm_pct')}%). "
            f"Top advisors: {', '.join(a['advisor_name'] for a in top_adv)}. "
            f"Needs attention: {', '.join(a['advisor_name'] for a in bot_adv)}."
        )
        prompt = (
            "You are the iPerform Insights and Coaching engine writing an executive summary for a "
            f"{d['scope_type']}-level wealth-management leader. Using ONLY the facts below, write 2-3 "
            "concise sentences: what the numbers say, the single biggest risk, and one focus area. "
            "Do not invent figures.\n\nFACTS: " + facts
        )
        try:
            summary = get_llm_client().generate(prompt, {"facts": facts}).strip()
        except LLMClientError:
            summary = facts

        insight = {
            "executive_summary": summary,
            "confidence": 0.82,
            "key_drivers": key_drivers,
            "watch_outs": watch_outs,
            "what_to_monitor": what_to_monitor,
        }
        return {
            "scope_type": d["scope_type"],
            "scope_id": d["scope_id"],
            "period": d["period"],
            "insight": insight,
            "grounding": facts,
        }
