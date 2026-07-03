from __future__ import annotations
from app.knowledge import get_knowledge_runtime
from datetime import datetime
from typing import Any

def _scope_multiplier(context: dict[str, Any]) -> float:
    persona = context.get("persona", "Advisor")
    scope_type = context.get("scope_type", "Advisor")
    return {"Advisor": 1.0, "MDW": 4.2, "DDW": 11.5, "Division": 18.0, "Firm": 48.0, "AGP": 2.4}.get(persona, {"Advisor":1.0,"Market":4.2,"Region":11.5}.get(scope_type, 1.0))

def _trace(workflow: str, agents: list[str]) -> dict[str, Any]:
    return {"execution_id": f"TRACE-{workflow.upper()}-{datetime.utcnow().strftime('%H%M%S')}", "workflow": workflow, "status": "success", "agents": [{"agent_name": agent, "status": "completed", "duration_ms": 120+i*37, "tool_calls": ["ContextService"] if i == 0 else ["TigerGraphMCP/Fallback", "MemoryService"]} for i, agent in enumerate(agents)]}

def _visible_widgets_for_persona(persona: str) -> list[str]:
    if persona == "Advisor":
        return ["advisor_kpis", "ai_insight", "coaching_card", "recommendations", "households", "crm", "agp_if_enrolled"]
    if persona == "MDW":
        return ["market_rollup", "advisor_comparison", "agp_review", "coaching_queue", "recommendation_approval"]
    if persona == "DDW":
        return ["division_rollup", "region_market_comparison", "mdw_review", "risk_watchlist"]
    if persona == "AGP":
        return ["agp_progress", "goals", "milestones", "mdw_ddw_reviews", "coaching_actions"]
    return ["firm_rollup", "division_performance", "top_bottom", "enterprise_opportunities"]

def get_dashboard_data(context: dict[str, Any]) -> dict[str, Any]:
    m = _scope_multiplier(context)
    persona = context.get("persona", "Advisor")
    revenue, managed, nnm, aum = 4_820_000*m, 2_180_000*m, 42_500_000*m, 96_300_000*m
    households = int(268 * min(m, 3.0))
    return {
        "context": context,
        "page_title": "Dashboard (Advisor View)" if persona == "Advisor" else f"{persona} Performance Dashboard",
        "role_summary": {"persona": persona, "visible_widgets": _visible_widgets_for_persona(persona)},
        "kpis": [
            {"label": "Total Revenue", "value": revenue, "display": f"${revenue/1_000_000:.2f}M", "change": 12.6, "status": "good", "icon": "DollarSign"},
            {"label": "Managed Revenue", "value": managed, "display": f"${managed/1_000_000:.2f}M", "change": 18.4, "status": "good", "icon": "Users"},
            {"label": "Managed Revenue %", "value": 45.2, "display": "45.2%", "change": 3.6, "status": "good", "icon": "PieChart"},
            {"label": "Households", "value": households, "display": f"{households:,}", "change": 8.1, "status": "good", "icon": "UsersRound"},
            {"label": "NCF", "value": 17985*m, "display": f"${17985*m:,.0f}", "change": 4.2, "status": "good", "icon": "BarChart3"},
            {"label": "AUM", "value": aum, "display": f"${aum/1_000_000:.1f}M", "change": 9.7, "status": "good", "icon": "Database"},
        ],
        "insight_summary": {"title": "Strong Revenue Growth Driven by Managed Accounts", "body": "Total revenue is up 12.6% versus prior year, primarily driven by managed account growth and new household acquisition.", "drivers": [{"label": "Managed Accounts", "value": "+18.4%", "status": "good"}, {"label": "New Households", "value": "+23.3%", "status": "good"}, {"label": "Fixed Income Revenue", "value": "-6.4%", "status": "bad"}]},
        "coaching_card": {"recommendation": "Expand managed relationships by reviewing households with investable assets and initiating managed account conversations.", "shoutout": "Great job growing Managed Accounts and adding new households.", "actions": ["Identify 15 high-potential households", "Schedule wealth review meetings", "Increase meeting frequency by 15%"]},
        "series": [{"month": mth, "revenue": revenue*val, "prior": revenue*(val-.03)} for mth,val in zip(["Jan","Feb","Mar","Apr","May"],[.10,.15,.21,.27,.31])],
        "product_mix": [{"category": "Managed Accounts", "share":45.2, "revenue":managed}, {"category":"Equities","share":24.6,"revenue":revenue*.246}, {"category":"Fixed Income","share":15.8,"revenue":revenue*.158}, {"category":"Mutual Funds","share":10.0,"revenue":revenue*.10}, {"category":"Other","share":4.4,"revenue":revenue*.044}],
        "opportunities": [{"name":"Managed Account Expansion","score":92,"priority":"High","impact":"$212K"}, {"name":"Equity Allocation Increase","score":88,"priority":"High","impact":"$156K"}, {"name":"Retirement Plan Consolidation","score":76,"priority":"Medium","impact":"$98K"}],
        "recommendations": [{"id":"REC-001","name":"Schedule Managed Account Review","score":91,"status":"active"}, {"id":"REC-002","name":"Increase Equity Allocation","score":84,"status":"active"}, {"id":"REC-003","name":"529 College Savings Discussion","score":77,"status":"active"}],
        "agent_trace": _trace("dashboard", ["SupervisorAgent","ContextAgent","InsightAgent","CoachingAgent","MemoryAgent"]),
    }

def get_page_data(page_id: str, context: dict[str, Any]) -> dict[str, Any]:
    return {"page_id": page_id, "context": context, "summary": get_dashboard_data(context), "agent_trace": _trace(page_id, ["SupervisorAgent","ContextAgent","GraphAgent","ExplainabilityAgent"])}

def run_what_if_simulation(request: dict[str, Any]) -> dict[str, Any]:
    base = get_dashboard_data(request)
    revenue, nnm, aum = base["kpis"][0]["value"], base["kpis"][5]["value"]*.052, base["kpis"][5]["value"]
    lift = request.get("meeting_increase_pct",0)*.12 + request.get("prospect_conversion_increase_pct",0)*.18 + request.get("managed_revenue_shift_pct",0)*.31 + request.get("nnm_increase_pct",0)*.08 + request.get("aum_increase_pct",0)*.04
    return {"baseline":{"revenue":revenue,"nnm":nnm,"aum":aum,"agp_goal":72}, "projected":{"revenue":revenue*(1+lift/100),"nnm":nnm*(1+request.get("nnm_increase_pct",0)/100),"aum":aum*(1+request.get("aum_increase_pct",0)/100),"agp_goal":min(100,72+lift)}, "changes":{"revenue_delta":revenue*(lift/100),"nnm_delta":nnm*(request.get("nnm_increase_pct",0)/100),"aum_delta":aum*(request.get("aum_increase_pct",0)/100),"goal_delta":lift}, "agent_trace": _trace("what_if", ["ScenarioAgent","PredictionAgent","RecommendationAgent","MemoryAgent"])}

def generate_recommendations(context: dict[str, Any]) -> dict[str, Any]:
    return {"context":context, "recommendations":[{"id":"REC-001","title":"Schedule Managed Account Review","priority":"High","status":"Generated","confidence":91,"impact":"$212K"}], "agent_trace": _trace("recommendations", ["OpportunityAgent","RecommendationAgent","ComplianceAgent","MemoryAgent"])}

def update_recommendation_feedback(request: dict[str, Any]) -> dict[str, Any]:
    action=request["action"]; colors={"accept":"green","complete":"green","reject":"red","ignore":"amber","modify":"blue"}
    return {"recommendation_id":request["recommendation_id"],"action":action,"ui_status_color":colors[action],"persisted_to":"mock_memory_and_feedback_store","learning_signal":f"Recommendation {action} captured for future learning.","agent_trace": _trace("feedback", ["FeedbackAgent","LearningAgent","MemoryAgent"])}

def ingest_document_mock(request: dict[str, Any]) -> dict[str, Any]:
    chunks=max(1, len(request.get("content",""))//800) if request.get("content") else 3
    return {"document_name":request["document_name"],"document_type":request.get("document_type","playbook"),"status":"indexed_mock","chroma_collection":"iperform_knowledge_base","chunks_created":chunks,"agent_trace": _trace("document_ingestion", ["DocumentAgent","ChunkingAgent","ChromaIndexAgent","KnowledgeAgent"])}
