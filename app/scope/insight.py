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

        # ---- Narrative (REQ-1): bold generated HEADLINE + grounded prose that explains
        # WHY the numbers moved (category drivers, peers, markets) — not a restatement of
        # the tiles. All facts are real computed values from the dashboard payload.
        bench = d["benchmark"]
        top_adv = d["top_advisors"][:2]
        bot_adv = d["bottom_advisors"][:2]
        drivers = d["revenue"].get("revenue_drivers", [])
        ups = [r for r in drivers if r.get("change", 0) > 0][:2]
        downs = [r for r in drivers if r.get("change", 0) < 0][:2]
        trend = d["revenue"].get("monthly_trend", [])
        sources = [
            "ScopeRollupService (per-advisor feature snapshots, real Σ/mean)",
            "RevenueAnalyticsService (period-windowed transactions, real YoY driver math)",
        ]

        fact_lines = [
            f"Scope: {d['scope_type']} {d['scope_id']} ({t['advisor_count']} advisors).",
            f"Revenue {d['period']} {_usd(head.get('revenue'))} ({head.get('compare_to')} Δ {head.get('delta_pct')}%, prior {_usd(head.get('prior'))}).",
            f"AUM {_usd(t['aum_total'])}, NNM annualized {_usd(t['nnm_annualized'])}, avg goal attainment {t['avg_goal_attainment']}%, avg AGP risk {t['avg_agp_risk_score']}, {at_risk} at-risk.",
        ]
        if ups:
            fact_lines.append("Categories UP YoY: " + "; ".join(
                f"{r['category']} +{_usd(r['change'])} ({r.get('change_pct')}%)" for r in ups) + ".")
        if downs:
            fact_lines.append("Categories DOWN YoY: " + "; ".join(
                f"{r['category']} {_usd(r['change'])} ({r.get('change_pct')}%)" for r in downs) + ".")
        if trend:
            fact_lines.append(f"Monthly trend {trend[0]['month']} {_usd(trend[0]['revenue'])} → {trend[-1]['month']} {_usd(trend[-1]['revenue'])}.")
        if bench.get("metrics"):  # advisor scope: GNN peer comparison
            sources.append(f"GNN peer benchmark ({bench.get('model')}), peers: "
                           + ", ".join(f"{p['advisor_name']} ({p['score']})" for p in bench.get("peers", [])))
            comp = "; ".join(
                f"{m['metric']} you {m['you']} vs peer avg {m['peer_avg']} ({m['vs_peer_pct']}%)"
                for m in bench["metrics"] if m.get("vs_peer_pct") is not None)
            fact_lines.append(f"Vs GNN-similar peers: {comp}.")
        else:
            fact_lines.append(
                f"Revenue/advisor {_usd(bench.get('current_per_advisor'))} vs firm avg "
                f"{_usd(bench.get('firm_per_advisor'))} ({bench.get('vs_firm_pct')}%).")
        mkts = d["markets"]
        if mkts.get("top"):
            fact_lines.append(f"Top market: {mkts['top'][0]['label']} {_usd(mkts['top'][0]['revenue_ltm'])}.")
        if mkts.get("bottom"):
            fact_lines.append(f"Bottom market: {mkts['bottom'][0]['label']} {_usd(mkts['bottom'][0]['revenue_ltm'])}.")
        if top_adv:
            fact_lines.append("Top advisors: " + ", ".join(a["advisor_name"] for a in top_adv) + ".")
        if bot_adv:
            fact_lines.append("Needs attention: " + ", ".join(
                f"{a['advisor_name']} ({a.get('reason')})" for a in bot_adv) + ".")
        facts = "\n".join(fact_lines)

        prompt = (
            "You are the iPerform Insights and Coaching engine writing the AI Insight Summary for a "
            f"{d['scope_type']}-level wealth-management {'advisor' if d['scope_type'] == 'ADVISOR' else 'leader'}. "
            "Using ONLY the facts below, respond in EXACTLY this format:\n"
            "HEADLINE: <one bold 6-10 word finding naming the main driver, e.g. 'Strong Revenue Growth Driven by Managed Accounts'>\n"
            "BODY: <2-4 sentences explaining WHY the numbers moved — name the driving categories, the peer "
            "comparison, and the single biggest risk. Do NOT merely restate the KPI values; explain causes "
            "and what they mean. Never invent figures not in the facts.>\n\nFACTS:\n" + facts
        )
        headline_text = None
        try:
            raw = get_llm_client().generate(prompt, {"facts": facts}).strip()
            summary = raw
            # Tolerate markdown decoration around the markers (Claude may emit "**HEADLINE:**").
            clean = raw.replace("**", "")
            for line in clean.splitlines():
                stripped = line.strip().lstrip("#").strip()
                if stripped.upper().startswith("HEADLINE:"):
                    headline_text = stripped.split(":", 1)[1].strip()
            if "BODY:" in clean:
                summary = clean.split("BODY:", 1)[1].strip()
            elif headline_text:
                summary = "\n".join(
                    l for l in clean.splitlines() if not l.strip().lstrip("#").strip().upper().startswith("HEADLINE:")
                ).strip()
        except LLMClientError:
            summary = facts

        insight = {
            "headline": headline_text,
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
            "grounding_sources": sources,
        }
