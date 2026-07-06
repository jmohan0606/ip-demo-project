from __future__ import annotations

"""Section 11.11 — make the architecture's own story visible in the product.

Two AI systems, one platform:
  - "iPerform Insights and Coaching" (proactive: insights, predictions, recommendations)
  - "iPerform Coach Q&A Assistant"   (reactive: Q&A / chat, user-initiated)

Exposes the poster artifacts as REAL data: which model/adapter actually served each function
this session (from the live registry + adapter modes), the Top-10 AI Protections status, and
the business-outcome mapping — so the demo ties directly back to the client's own design.
"""

from fastapi import APIRouter

from app.config.settings import get_settings
from app.shared.responses import ok

router = APIRouter(prefix="/architecture", tags=["Architecture"])


@router.get("/model-strategy")
def model_strategy():
    """Model Strategy (Per Function) — which real model/adapter served each function now."""
    from app.ml import registry

    settings = get_settings()
    serving = {e["name"]: e for e in registry.list_entries() if e.get("quality_gate") == "passed"}

    def served(model_name: str, fallback: str) -> str:
        return model_name if model_name in serving else fallback

    llm = settings.llm_client_mode
    rows = [
        {"function": "Insight Agent", "system": "iPerform Insights and Coaching",
         "served_by": f"LLM ({llm})", "kind": "LLM"},
        {"function": "Coaching Agent", "system": "iPerform Insights and Coaching",
         "served_by": f"LLM ({llm})", "kind": "LLM"},
        {"function": "Revenue-Decline Prediction", "system": "iPerform Insights and Coaching",
         "served_by": served("revenue-decline-xgb", "iPerform Risk Scorecard (deterministic)"), "kind": "ML"},
        {"function": "AGP Off-Track Prediction", "system": "iPerform Insights and Coaching",
         "served_by": served("agp-off-track-xgb", "iPerform Risk Scorecard (deterministic fallback)"), "kind": "ML"},
        {"function": "Revenue Forecast", "system": "iPerform Insights and Coaching",
         "served_by": served("revenue-forecast-gru", "seasonal-naive baseline"), "kind": "DL"},
        {"function": "Household Churn", "system": "iPerform Insights and Coaching",
         "served_by": served("household-churn-xgb", "indicative (below gate)"), "kind": "ML"},
        {"function": "Graph Embeddings / Similarity", "system": "iPerform Insights and Coaching",
         "served_by": registry.active_embedding_model(), "kind": "GNN"},
        {"function": "Activity Anomaly", "system": "iPerform Insights and Coaching",
         "served_by": served("activity-anomaly-iforest", "off"), "kind": "ML"},
        {"function": "Recommendation Ranking", "system": "iPerform Insights and Coaching",
         "served_by": "contextual bandit + outcome affinity", "kind": "RL"},
        {"function": "Coach Q&A / RAG", "system": "iPerform Coach Q&A Assistant",
         "served_by": f"LLM ({llm}) + {settings.embedding_client_mode} embeddings", "kind": "RAG"},
        {"function": "Agentic Reasoning", "system": "iPerform Coach Q&A Assistant",
         "served_by": f"multi-agent graph + LLM ({llm})", "kind": "Agent"},
        {"function": "Graph Access", "system": "Both",
         "served_by": f"GraphClient ({settings.graph_client_mode})", "kind": "Adapter"},
    ]
    return ok(data={
        "systems": {
            "proactive": {"label": "iPerform Insights and Coaching",
                          "description": "Insights, predictions, recommendations — delivered automatically."},
            "reactive": {"label": "iPerform Coach Q&A Assistant",
                         "description": "Q&A and coaching — user-initiated."},
        },
        "model_strategy": rows,
    })


# Top-10 AI Protections (poster) with honest status against what this build actually implements.
_PROTECTIONS = [
    ("Grounding / hallucination guard", "implemented",
     "RAG answers cite retrieved chunks with similarity scores; below-floor → honest not-found."),
    ("Evidence & lineage for every AI output", "implemented",
     "Every prediction/recommendation persists contributions + reasoning trace + source ids."),
    ("Compliance guardrails", "implemented",
     "Compliance agent: prohibited-claims / suitability-disclosure / $50k supervisory / <0.60 confidence."),
    ("Model quality gates (no over-claiming)", "implemented",
     "2 of 6 models correctly gated to fallback; real held-out metrics in the registry."),
    ("Honest small-data caveats", "implemented",
     "Model cards + UI state demo-scale limits verbatim; effects shown truthfully, not tuned."),
    ("Confidence surfacing", "implemented",
     "Confidence % on predictions/recommendations/answers; low-confidence guardrail."),
    ("Human-in-the-loop / non-alarmist framing", "implemented",
     "Activity Pattern Review is care-framed with explicit human disposition; feedback accept/reject."),
    ("PII / data minimization", "partial",
     "Demo uses synthetic data; no real PII. Field-level minimization not separately enforced."),
    ("Prompt-injection / input validation", "partial",
     "RAG restricts to retrieved context; no dedicated injection classifier yet."),
    ("Audit log / model governance", "partial",
     "Model registry + Model Strategy + reasoning traces provide governance; a dedicated immutable audit log is future work."),
]


@router.get("/ai-protections")
def ai_protections():
    """Top-10 AI Protections status (implemented / partial / not-yet) — honest self-assessment."""
    items = [{"protection": p, "status": s, "detail": d} for p, s, d in _PROTECTIONS]
    counts = {"implemented": 0, "partial": 0, "not_yet": 0}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return ok(data={"protections": items, "counts": counts})


# Business outcomes (poster) mapped to the KPIs that evidence them.
_OUTCOMES = {
    "revenue_ltm": "Increase Revenue",
    "aum_total": "Increase AUM",
    "nnm_3m": "Increase NCF",
    "goal_attainment": "Improve Goal Attainment",
    "advisor_productivity": "Increase Advisor Productivity",
}


@router.get("/business-outcomes")
def business_outcomes():
    """Which business outcome each headline KPI maps to (poster Business Outcomes)."""
    return ok(data={"outcomes": _OUTCOMES})
