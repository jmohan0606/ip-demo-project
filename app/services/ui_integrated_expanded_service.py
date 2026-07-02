from app.knowledge import get_knowledge_runtime
from __future__ import annotations

from datetime import datetime
from typing import Any


def _trace(workflow: str, agents: list[str]) -> dict[str, Any]:
    return {
        "execution_id": f"TRACE-{workflow.upper()}-{datetime.utcnow().strftime('%H%M%S')}",
        "workflow": workflow,
        "status": "success",
        "agents": [
            {
                "agent_name": agent,
                "status": "completed",
                "duration_ms": 110 + i * 41,
                "tool_calls": ["TigerGraphMCP/Fallback", "Chroma/Fallback", "MemoryService"][: 1 + (i % 3)],
            }
            for i, agent in enumerate(agents)
        ],
    }


def _persona_factor(context: dict[str, Any]) -> float:
    persona = context.get("persona", "Advisor")
    return {"Advisor": 1.0, "MDW": 4.0, "DDW": 12.0, "Firm": 40.0, "Division": 18.0, "Region": 9.0, "Market": 4.0}.get(persona, 1.0)


def get_advisor_360_data(context: dict[str, Any]) -> dict[str, Any]:
    factor = _persona_factor(context)
    return {
        "context": context,
        "advisor": {
            "advisor_id": context.get("scope_id", "ADV0001"),
            "name": "Alex Morgan" if context.get("persona") == "Advisor" else f"{context.get('persona')} Rollup",
            "market": "Downtown Market",
            "agp_status": "At Risk",
            "revenue_ytd": 4_820_000 * factor,
            "aum": 96_300_000 * factor,
            "nnm": 7_250_000 * factor,
            "ncf": 1_985_000 * factor,
        },
        "households": [
            {"id": "HH-001", "name": "Parker Family", "aum": 18_200_000, "nnm": 1_120_000, "status": "good", "next_action": "Managed account review"},
            {"id": "HH-002", "name": "Rivera Trust", "aum": 11_700_000, "nnm": -340_000, "status": "bad", "next_action": "Outflow recovery call"},
            {"id": "HH-003", "name": "Chen Foundation", "aum": 24_900_000, "nnm": 2_480_000, "status": "good", "next_action": "Fixed income ladder review"},
        ],
        "crm": [
            {"date": "2026-06-04", "type": "Meeting", "subject": "Portfolio review", "status": "Completed"},
            {"date": "2026-06-09", "type": "Call", "subject": "Liquidity event", "status": "Follow-up"},
            {"date": "2026-06-13", "type": "Note", "subject": "AGP coaching note", "status": "Logged"},
        ],
        "agent_trace": _trace("advisor_360", ["SupervisorAgent", "ContextAgent", "GraphAgent", "Advisor360Agent", "MemoryAgent"]),
    }


def get_recommendations_workspace_data(context: dict[str, Any]) -> dict[str, Any]:
    recs = [
        {"id": "REC-001", "title": "Schedule Managed Account Review", "priority": "High", "confidence": 91, "impact": "$212K", "compliance": "Passed", "status": "Generated"},
        {"id": "REC-002", "title": "Launch NNM Recovery Sequence", "priority": "High", "confidence": 86, "impact": "$156K", "compliance": "Review Required", "status": "Generated"},
        {"id": "REC-003", "title": "Increase Client Meeting Cadence", "priority": "Medium", "confidence": 79, "impact": "$84K", "compliance": "Passed", "status": "Generated"},
    ]
    return {
        "context": context,
        "recommendations": recs,
        "opportunities": [
            {"id": "OPP-001", "title": "Managed Account Expansion", "score": 92, "status": "good"},
            {"id": "OPP-002", "title": "NNM Outflow Recovery", "score": 88, "status": "warn"},
            {"id": "OPP-003", "title": "Fixed Income Ladder", "score": 76, "status": "good"},
        ],
        "agent_trace": _trace("recommendations_workspace", ["OpportunityAgent", "RecommendationAgent", "ComplianceAgent", "FeedbackAgent", "MemoryAgent"]),
    }


def get_graph_explorer_data(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "context": context,
        "nodes": [
            {"id": "ADV0001", "label": "Alex Morgan", "type": "Advisor", "score": 88},
            {"id": "HH001", "label": "Parker Family", "type": "Household", "score": 91},
            {"id": "ACCT001", "label": "Managed Account", "type": "Account", "score": 83},
            {"id": "PROD001", "label": "Managed Accounts", "type": "Product", "score": 84},
            {"id": "OPP001", "label": "Expansion Opportunity", "type": "Opportunity", "score": 92},
            {"id": "REC001", "label": "Schedule Review", "type": "Recommendation", "score": 91},
            {"id": "MEM001", "label": "Reasoning Memory", "type": "Memory", "score": 86},
        ],
        "edges": [
            {"source": "ADV0001", "target": "HH001", "label": "SERVES"},
            {"source": "HH001", "target": "ACCT001", "label": "OWNS"},
            {"source": "ACCT001", "target": "PROD001", "label": "HOLDS"},
            {"source": "HH001", "target": "OPP001", "label": "HAS_OPPORTUNITY"},
            {"source": "OPP001", "target": "REC001", "label": "GENERATES"},
            {"source": "REC001", "target": "MEM001", "label": "USED_MEMORY"},
        ],
        "agent_trace": _trace("graph_explorer", ["GraphAgent", "TigerGraphMCPTool", "ExplainabilityAgent"]),
    }


def get_features_embeddings_data(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "context": context,
        "feature_sets": [
            {"name": "Advisor Revenue Features", "entity": "Advisor", "features": 38, "freshness": "Current", "status": "good"},
            {"name": "Household Behavior Features", "entity": "Household", "features": 44, "freshness": "Current", "status": "good"},
            {"name": "Opportunity Propensity Features", "entity": "Opportunity", "features": 27, "freshness": "1 day", "status": "warn"},
        ],
        "similar_entities": [
            {"entity": "Advisor Maya Chen", "similarity": 0.92, "reason": "Similar product mix and growth trajectory"},
            {"entity": "Advisor Noah Williams", "similarity": 0.87, "reason": "Similar AGP cohort and revenue stage"},
            {"entity": "Household Rivera Trust", "similarity": 0.81, "reason": "Similar liquidity profile"},
        ],
        "embedding_plot": [
            {"x": 0.12, "y": 0.84, "label": "Alex Morgan"},
            {"x": 0.18, "y": 0.79, "label": "Maya Chen"},
            {"x": 0.22, "y": 0.73, "label": "Noah Williams"},
            {"x": 0.61, "y": 0.22, "label": "Different Peer"},
        ],
        "agent_trace": _trace("features_embeddings", ["FeatureAgent", "EmbeddingAgent", "SimilarityAgent"]),
    }


def get_memory_explainability_data(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "context": context,
        "timeline": [
            {"date": "2026-06-01", "type": "Conversation", "title": "Advisor asked about revenue decline", "status": "good"},
            {"date": "2026-06-03", "type": "Reasoning", "title": "Managed revenue gap detected", "status": "warn"},
            {"date": "2026-06-05", "type": "Recommendation", "title": "Managed account review generated", "status": "good"},
            {"date": "2026-06-10", "type": "Feedback", "title": "Recommendation accepted", "status": "good"},
        ],
        "explainability_path": [
            "Revenue Mix Gap",
            "Peer Benchmark Gap",
            "Household Suitability",
            "Compliance Playbook",
            "Recommendation",
        ],
        "evidence": [
            {"source": "TigerGraph", "item": "Advisor-Household-Account path"},
            {"source": "Chroma", "item": "Managed account review playbook"},
            {"source": "Feature Store", "item": "Managed revenue mix feature"},
        ],
        "agent_trace": _trace("memory_explainability", ["MemoryAgent", "ExplainabilityAgent", "GraphAgent", "KnowledgeAgent"]),
    }


def search_knowledge(request: dict[str, Any]) -> dict[str, Any]:
    query = request.get("query", "managed account growth playbook")
    runtime_result = get_knowledge_runtime().search(query, top_k=5).to_dict()
    data = runtime_result.get("data", {})
    return {
        "query": query,
        "results": data.get("results", []),
        "collection": data.get("collection", "iperform_knowledge_base"),
        "knowledge_runtime": runtime_result,
        "agent_trace": _trace("knowledge_search", ["KnowledgeAgent", "ChromaSearchTool", "CitationAgent"]),
    }
