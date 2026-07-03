from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import ADVISOR, USER, vset


def _user_scope_vertices(store: FoundationGraphStore, user_id: str) -> dict[str, list[str]]:
    return {
        "firms": store.out_ids("phx_dm_user_scoped_to_firm", user_id),
        "divisions": store.out_ids("phx_dm_user_scoped_to_division", user_id),
        "regions": store.out_ids("phx_dm_user_scoped_to_region", user_id),
        "markets": store.out_ids("phx_dm_user_scoped_to_market", user_id),
        "branches": store.out_ids("phx_dm_user_scoped_to_branch", user_id),
    }


def _authorized_advisor_ids(store: FoundationGraphStore, user_id: str) -> set[str]:
    """Mirror of the GQ-031/040 authorization ladder: represented advisors plus
    every advisor under any scope the user is assigned to; ADMIN/AI_OPS see all."""
    user = store.vertex(USER, user_id) or {}
    if user.get("role_code") in {"ADMIN", "AI_OPS"}:
        return set(store.all_vertices(ADVISOR).keys())
    authorized: set[str] = set(store.out_ids("phx_dm_user_represents_advisor", user_id))
    scopes = _user_scope_vertices(store, user_id)
    for branch_id in scopes["branches"]:
        authorized.update(store.in_ids("phx_dm_advisor_in_branch", branch_id))
    market_ids = list(scopes["markets"])
    for region_id in scopes["regions"]:
        market_ids.extend(store.in_ids("phx_dm_market_in_region", region_id))
    region_ids = []
    for division_id in scopes["divisions"]:
        region_ids.extend(store.in_ids("phx_dm_region_in_division", division_id))
    for firm_id in scopes["firms"]:
        for division_id in store.in_ids("phx_dm_division_in_firm", firm_id):
            region_ids.extend(store.in_ids("phx_dm_region_in_division", division_id))
    for region_id in region_ids:
        market_ids.extend(store.in_ids("phx_dm_market_in_region", region_id))
    for market_id in market_ids:
        authorized.update(store.in_ids("phx_dm_advisor_in_market", market_id))
    return authorized


def _advisor_context_sets(store: FoundationGraphStore, advisor_id: str) -> dict[str, list[dict]]:
    return {
        "features": vset(store, "phx_dm_feature_snapshot", store.out_ids("phx_dm_advisor_has_feature_snapshot", advisor_id)),
        "memories": vset(store, "phx_dm_context_memory", store.in_ids("phx_dm_memory_for_advisor", advisor_id)),
        "predictions": vset(store, "phx_dm_prediction_result", store.in_ids("phx_dm_prediction_for_advisor", advisor_id)),
        "opportunities": vset(store, "phx_dm_opportunity", store.in_ids("phx_dm_opportunity_for_advisor", advisor_id)),
        "recommendations": vset(store, "phx_dm_recommendation", store.in_ids("phx_dm_recommendation_for_advisor", advisor_id)),
        "activities": vset(store, "phx_dm_crm_activity", store.in_ids("phx_dm_activity_for_advisor", advisor_id)),
    }


@mock_query("get_context_for_agent")
def get_context_for_agent(store: FoundationGraphStore, params: dict) -> list[dict]:
    user_id = str(params.get("persona_user_id") or "")
    subject_id = str(params.get("subject_id") or "")
    query_intent = str(params.get("query_intent") or "")

    user = store.vertex(USER, user_id) or {}
    privileged = user.get("role_code") in {"ADMIN", "AI_OPS"}
    authorized = subject_id in _authorized_advisor_ids(store, user_id)
    scopes = _user_scope_vertices(store, user_id)
    context = _advisor_context_sets(store, subject_id) if authorized else {
        k: [] for k in ("features", "memories", "predictions", "opportunities", "recommendations", "activities")
    }
    return [
        {
            "query_intent": query_intent,
            "user": vset(store, USER, [user_id]),
            "user_firms": vset(store, "phx_dm_firm", scopes["firms"]),
            "user_divisions": vset(store, "phx_dm_division", scopes["divisions"]),
            "user_regions": vset(store, "phx_dm_region", scopes["regions"]),
            "user_markets": vset(store, "phx_dm_market", scopes["markets"]),
            "user_branches": vset(store, "phx_dm_branch", scopes["branches"]),
            "subject": vset(store, ADVISOR, [subject_id]) if authorized else [],
            **context,
            "playbooks": vset(store, "phx_dm_playbook", list(store.all_vertices("phx_dm_playbook"))[:10]),
            "documents": vset(store, "phx_dm_document", list(store.all_vertices("phx_dm_document"))[:10]),
            "privileged_user": privileged,
        }
    ]


@mock_query("get_insight_coaching_context")
def get_insight_coaching_context(store: FoundationGraphStore, params: dict) -> list[dict]:
    user_id = str(params.get("persona_user_id") or "")
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")
    subject_id = str(params.get("subject_id") or "")

    user = store.vertex(USER, user_id) or {}
    privileged = user.get("role_code") in {"ADMIN", "AI_OPS"}
    authorized = subject_id in _authorized_advisor_ids(store, user_id)
    context = _advisor_context_sets(store, subject_id) if authorized else {
        k: [] for k in ("features", "memories", "predictions", "opportunities", "recommendations", "activities")
    }
    return [
        {
            "user": vset(store, USER, [user_id]),
            "scope_type": scope_type,
            "scope_id": scope_id,
            "subject": vset(store, ADVISOR, [subject_id]) if authorized else [],
            "features": context["features"],
            "predictions": context["predictions"],
            "opportunities": context["opportunities"],
            "recommendations": context["recommendations"],
            "memories": context["memories"],
            "crm_activities": context["activities"],
            "enrollments": vset(store, "phx_dm_agp_enrollment", store.out_ids("phx_dm_advisor_has_agp_enrollment", subject_id)) if authorized else [],
            "privileged_user": privileged,
        }
    ]


@mock_query("get_memory_timeline")
def get_memory_timeline(store: FoundationGraphStore, params: dict) -> list[dict]:
    subject_type = (params.get("subject_type") or "").upper()
    subject_id = str(params.get("subject_id") or "")
    memory_ids = [
        memory_id
        for memory_id, attrs in store.all_vertices("phx_dm_context_memory").items()
        if str(attrs.get("subject_type", "")).upper() == subject_type and str(attrs.get("subject_id")) == subject_id
    ]
    memory_ids.sort(
        key=lambda mid: str((store.vertex("phx_dm_context_memory", mid) or {}).get("created_at") or ""), reverse=True
    )
    turn_ids: list[str] = []
    reasoning_ids: list[str] = []
    for memory_id in memory_ids:
        turn_ids.extend(store.in_ids("phx_dm_conversation_creates_memory", memory_id))
        reasoning_ids.extend(store.in_ids("phx_dm_reasoning_uses_memory", memory_id))
    return [
        {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "memories": vset(store, "phx_dm_context_memory", memory_ids),
            "conversation_turns": vset(store, "phx_dm_conversation_turn", turn_ids),
            "reasoning": vset(store, "phx_dm_reasoning_trace", reasoning_ids),
        }
    ]


@mock_query("get_reasoning_trace")
def get_reasoning_trace(store: FoundationGraphStore, params: dict) -> list[dict]:
    artifact_type = (params.get("artifact_type") or "").upper()
    artifact_id = str(params.get("artifact_id") or "")
    reasoning_ids = [
        rid
        for rid, attrs in store.all_vertices("phx_dm_reasoning_trace").items()
        if str(attrs.get("artifact_type", "")).upper() == artifact_type and str(attrs.get("artifact_id")) == artifact_id
    ]
    memories: list[str] = []
    features: list[str] = []
    chunks: list[str] = []
    activities: list[str] = []
    transactions: list[str] = []
    for rid in reasoning_ids:
        memories.extend(store.out_ids("phx_dm_reasoning_uses_memory", rid))
        features.extend(store.out_ids("phx_dm_reasoning_uses_feature_snapshot", rid))
        chunks.extend(store.out_ids("phx_dm_reasoning_uses_document_chunk", rid))
        activities.extend(store.out_ids("phx_dm_reasoning_uses_crm_activity", rid))
        transactions.extend(store.out_ids("phx_dm_reasoning_uses_transaction", rid))
    return [
        {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "reasoning": vset(store, "phx_dm_reasoning_trace", reasoning_ids),
            "memories": vset(store, "phx_dm_context_memory", memories),
            "features": vset(store, "phx_dm_feature_snapshot", features),
            "document_chunks": vset(store, "phx_dm_document_chunk", chunks),
            "crm_activities": vset(store, "phx_dm_crm_activity", activities),
            "transactions": vset(store, "phx_dm_revenue_transaction", transactions),
        }
    ]


@mock_query("get_notifications_for_user")
def get_notifications_for_user(store: FoundationGraphStore, params: dict) -> list[dict]:
    user_id = str(params.get("user_id") or "")
    status = (params.get("status") or "ALL").upper()
    limit = int(params.get("result_limit") or 20)
    notification_ids = []
    for notification_id in store.in_ids("phx_dm_notification_for_user", user_id):
        attrs = store.vertex("phx_dm_notification", notification_id) or {}
        if status == "ALL" or str(attrs.get("status", "")).upper() == status:
            notification_ids.append(notification_id)
        if len(notification_ids) >= limit:
            break
    return [
        {
            "user": vset(store, USER, [user_id]),
            "notifications": vset(store, "phx_dm_notification", notification_ids),
        }
    ]


@mock_query("get_agent_execution_trace")
def get_agent_execution_trace(store: FoundationGraphStore, params: dict) -> list[dict]:
    execution_id = str(params.get("execution_id") or "")
    return [
        {
            "execution": vset(store, "phx_dm_agent_execution", [execution_id]),
            "tool_calls": vset(store, "phx_dm_tool_call", store.out_ids("phx_dm_execution_has_tool_call", execution_id)),
            "evaluations": vset(store, "phx_dm_evaluation_result", store.out_ids("phx_dm_execution_has_evaluation", execution_id)),
            "guardrails": vset(store, "phx_dm_guardrail_event", store.out_ids("phx_dm_execution_has_guardrail_event", execution_id)),
            "reasoning": vset(store, "phx_dm_reasoning_trace", store.out_ids("phx_dm_execution_generated_reasoning", execution_id)),
        }
    ]
