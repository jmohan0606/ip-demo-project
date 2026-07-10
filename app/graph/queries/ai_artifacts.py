from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore
from app.graph.queries.common import resolve_scope_advisor_ids, vset


def _entity_edge(prefix: str, entity_type: str) -> str:
    """Edge name for advisor/household/account/product ownership of AI artifacts,
    e.g. ('has_feature_snapshot', 'ADVISOR') -> phx_dm_advisor_has_feature_snapshot."""
    return f"phx_dm_{entity_type.lower()}_{prefix}"


@mock_query("get_feature_snapshot")
def get_feature_snapshot(store: FoundationGraphStore, params: dict) -> list[dict]:
    entity_type = (params.get("entity_type") or "").upper()
    entity_id = str(params.get("entity_id") or "")
    snapshots = [
        fs_id
        for fs_id, attrs in store.all_vertices("phx_dm_feature_snapshot").items()
        if str(attrs.get("entity_type", "")).upper() == entity_type and str(attrs.get("entity_id")) == entity_id
    ]
    return [
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "feature_snapshots": vset(store, "phx_dm_feature_snapshot", snapshots),
        }
    ]


@mock_query("get_feature_lineage")
def get_feature_lineage(store: FoundationGraphStore, params: dict) -> list[dict]:
    fs_id = str(params.get("feature_snapshot_id") or "")
    return [
        {
            "feature_snapshot": vset(store, "phx_dm_feature_snapshot", [fs_id]),
            "advisors": vset(store, "phx_dm_advisor", store.in_ids("phx_dm_advisor_has_feature_snapshot", fs_id)),
            "households": vset(store, "phx_dm_household", store.in_ids("phx_dm_household_has_feature_snapshot", fs_id)),
            "accounts": vset(store, "phx_dm_account", store.in_ids("phx_dm_account_has_feature_snapshot", fs_id)),
            "products": vset(store, "phx_dm_product", store.in_ids("phx_dm_product_has_feature_snapshot", fs_id)),
            "predictions": vset(store, "phx_dm_prediction_result", store.in_ids("phx_dm_prediction_uses_feature_snapshot", fs_id)),
            "opportunities": vset(store, "phx_dm_opportunity", store.in_ids("phx_dm_opportunity_uses_feature_snapshot", fs_id)),
            "recommendations": vset(store, "phx_dm_recommendation", store.in_ids("phx_dm_recommendation_uses_feature_snapshot", fs_id)),
            "reasoning": vset(store, "phx_dm_reasoning_trace", store.in_ids("phx_dm_reasoning_uses_feature_snapshot", fs_id)),
        }
    ]


@mock_query("get_embeddings_for_entity")
def get_embeddings_for_entity(store: FoundationGraphStore, params: dict) -> list[dict]:
    entity_type = (params.get("entity_type") or "").upper()
    entity_id = str(params.get("entity_id") or "")
    edge = _entity_edge("has_embedding", entity_type)
    return [
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "embeddings": vset(store, "phx_dm_embedding", store.out_ids(edge, entity_id)),
        }
    ]


@mock_query("get_similar_entities")
def get_similar_entities(store: FoundationGraphStore, params: dict) -> list[dict]:
    entity_type = (params.get("entity_type") or "").upper()
    entity_id = str(params.get("entity_id") or "")
    result_limit = int(params.get("result_limit") or 10)
    min_score = float(params.get("min_score") or 0)

    match_ids = [
        match_id
        for match_id, attrs in store.all_vertices("phx_dm_similarity_match").items()
        if str(attrs.get("entity_type", "")).upper() == entity_type
        and str(attrs.get("source_entity_id")) == entity_id
        and float(attrs.get("similarity_score") or 0) >= min_score
    ]
    match_ids.sort(
        key=lambda mid: -float((store.vertex("phx_dm_similarity_match", mid) or {}).get("similarity_score") or 0)
    )
    match_ids = match_ids[:result_limit]

    similar: dict[str, list[str]] = {"advisor": [], "household": [], "account": [], "product": []}
    for match_id in match_ids:
        for kind in similar:
            similar[kind].extend(store.out_ids(f"phx_dm_similarity_match_targets_{kind}", match_id))
    return [
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "matches": vset(store, "phx_dm_similarity_match", match_ids),
            "similar_advisors": vset(store, "phx_dm_advisor", similar["advisor"]),
            "similar_households": vset(store, "phx_dm_household", similar["household"]),
            "similar_accounts": vset(store, "phx_dm_account", similar["account"]),
            "similar_products": vset(store, "phx_dm_product", similar["product"]),
        }
    ]


def _artifacts_for_target(store: FoundationGraphStore, vertex_type: str, target_type: str, target_id: str) -> list[str]:
    return [
        vid
        for vid, attrs in store.all_vertices(vertex_type).items()
        if str(attrs.get("target_type", "")).upper() == target_type and str(attrs.get("target_id")) == target_id
    ]


@mock_query("get_predictions")
def get_predictions(store: FoundationGraphStore, params: dict) -> list[dict]:
    target_type = (params.get("target_type") or "").upper()
    target_id = str(params.get("target_id") or "")
    prediction_ids = _artifacts_for_target(store, "phx_dm_prediction_result", target_type, target_id)
    feature_ids: list[str] = []
    reasoning_ids: list[str] = []
    for prediction_id in prediction_ids:
        feature_ids.extend(store.out_ids("phx_dm_prediction_uses_feature_snapshot", prediction_id))
        reasoning_ids.extend(store.in_ids("phx_dm_reasoning_for_prediction", prediction_id))
    return [
        {
            "target_type": target_type,
            "target_id": target_id,
            "predictions": vset(store, "phx_dm_prediction_result", prediction_ids),
            "features": vset(store, "phx_dm_feature_snapshot", feature_ids),
            "reasoning": vset(store, "phx_dm_reasoning_trace", reasoning_ids),
        }
    ]


@mock_query("get_ai_opportunities")
def get_ai_opportunities(store: FoundationGraphStore, params: dict) -> list[dict]:
    target_type = (params.get("target_type") or "").upper()
    target_id = str(params.get("target_id") or "")
    opportunity_ids = _artifacts_for_target(store, "phx_dm_opportunity", target_type, target_id)
    predictions: list[str] = []
    crm_opportunities: list[str] = []
    features: list[str] = []
    recommendations: list[str] = []
    reasoning: list[str] = []
    for opportunity_id in opportunity_ids:
        predictions.extend(store.out_ids("phx_dm_opportunity_derived_from_prediction", opportunity_id))
        crm_opportunities.extend(store.out_ids("phx_dm_ai_opportunity_derived_from_crm_opportunity", opportunity_id))
        features.extend(store.out_ids("phx_dm_opportunity_uses_feature_snapshot", opportunity_id))
        recommendations.extend(store.in_ids("phx_dm_recommendation_addresses_opportunity", opportunity_id))
        reasoning.extend(store.in_ids("phx_dm_reasoning_for_opportunity", opportunity_id))
    return [
        {
            "target_type": target_type,
            "target_id": target_id,
            "opportunities": vset(store, "phx_dm_opportunity", opportunity_ids),
            "predictions": vset(store, "phx_dm_prediction_result", predictions),
            "crm_opportunities": vset(store, "phx_dm_crm_opportunity", crm_opportunities),
            "features": vset(store, "phx_dm_feature_snapshot", features),
            "recommendations": vset(store, "phx_dm_recommendation", recommendations),
            "reasoning": vset(store, "phx_dm_reasoning_trace", reasoning),
        }
    ]


def _recommendation_lineage(store: FoundationGraphStore, recommendation_ids: list[str]) -> dict[str, list[str]]:
    lineage: dict[str, list[str]] = {"opportunities": [], "predictions": [], "features": [], "playbooks": [], "reasoning": []}
    for rec_id in recommendation_ids:
        lineage["opportunities"].extend(store.out_ids("phx_dm_recommendation_addresses_opportunity", rec_id))
        lineage["predictions"].extend(store.out_ids("phx_dm_recommendation_based_on_prediction", rec_id))
        lineage["features"].extend(store.out_ids("phx_dm_recommendation_uses_feature_snapshot", rec_id))
        lineage["playbooks"].extend(store.out_ids("phx_dm_recommendation_uses_playbook", rec_id))
        lineage["reasoning"].extend(store.in_ids("phx_dm_reasoning_for_recommendation", rec_id))
    return lineage


@mock_query("get_recommendations")
def get_recommendations(store: FoundationGraphStore, params: dict) -> list[dict]:
    target_type = (params.get("target_type") or "").upper()
    target_id = str(params.get("target_id") or "")
    edge = {"ADVISOR": "phx_dm_recommendation_for_advisor", "HOUSEHOLD": "phx_dm_recommendation_for_household", "ACCOUNT": "phx_dm_recommendation_for_account"}.get(target_type)
    recommendation_ids = store.in_ids(edge, target_id) if edge else []
    lineage = _recommendation_lineage(store, recommendation_ids)
    return [
        {
            "target_type": target_type,
            "target_id": target_id,
            "recommendations": vset(store, "phx_dm_recommendation", recommendation_ids),
            "opportunities": vset(store, "phx_dm_opportunity", lineage["opportunities"]),
            "predictions": vset(store, "phx_dm_prediction_result", lineage["predictions"]),
            "features": vset(store, "phx_dm_feature_snapshot", lineage["features"]),
            "playbooks": vset(store, "phx_dm_playbook", lineage["playbooks"]),
            "reasoning": vset(store, "phx_dm_reasoning_trace", lineage["reasoning"]),
        }
    ]


@mock_query("get_recommendation_detail")
def get_recommendation_detail(store: FoundationGraphStore, params: dict) -> list[dict]:
    recommendation_id = str(params.get("recommendation_id") or "")
    lineage = _recommendation_lineage(store, [recommendation_id])
    feedback_ids = store.in_ids("phx_dm_feedback_for_recommendation", recommendation_id)
    outcome_ids: list[str] = []
    for feedback_id in feedback_ids:
        outcome_ids.extend(store.in_ids("phx_dm_outcome_for_feedback", feedback_id))
    learning_ids: list[str] = []
    for outcome_id in outcome_ids:
        learning_ids.extend(store.in_ids("phx_dm_learning_from_outcome", outcome_id))
    return [
        {
            "recommendation": vset(store, "phx_dm_recommendation", [recommendation_id]),
            "opportunities": vset(store, "phx_dm_opportunity", lineage["opportunities"]),
            "predictions": vset(store, "phx_dm_prediction_result", lineage["predictions"]),
            "features": vset(store, "phx_dm_feature_snapshot", lineage["features"]),
            "playbooks": vset(store, "phx_dm_playbook", lineage["playbooks"]),
            "reasoning": vset(store, "phx_dm_reasoning_trace", lineage["reasoning"]),
            "feedback": vset(store, "phx_dm_feedback_event", feedback_ids),
            "outcomes": vset(store, "phx_dm_outcome_event", outcome_ids),
            "learning": vset(store, "phx_dm_learning_signal", learning_ids),
        }
    ]


@mock_query("get_feedback_learning_history")
def get_feedback_learning_history(store: FoundationGraphStore, params: dict) -> list[dict]:
    recommendation_id = str(params.get("recommendation_id") or "")
    feedback_ids = store.in_ids("phx_dm_feedback_for_recommendation", recommendation_id)
    outcome_ids: list[str] = []
    for feedback_id in feedback_ids:
        outcome_ids.extend(store.in_ids("phx_dm_outcome_for_feedback", feedback_id))
    learning_ids: list[str] = []
    for outcome_id in outcome_ids:
        learning_ids.extend(store.in_ids("phx_dm_learning_from_outcome", outcome_id))
    learning_links = store.in_ids("phx_dm_learning_updates_recommendation", recommendation_id)
    return [
        {
            "recommendation": vset(store, "phx_dm_recommendation", [recommendation_id]),
            "feedback": vset(store, "phx_dm_feedback_event", feedback_ids),
            "outcomes": vset(store, "phx_dm_outcome_event", outcome_ids),
            "learning": vset(store, "phx_dm_learning_signal", learning_ids),
            "learning_links": vset(store, "phx_dm_learning_signal", learning_links),
        }
    ]


@mock_query("get_recommendation_adoption_learning_summary")
def get_recommendation_adoption_learning_summary(store: FoundationGraphStore, params: dict) -> list[dict]:
    scope_type = (params.get("scope_type") or "").upper()
    scope_id = str(params.get("scope_id") or "")
    advisor_ids = resolve_scope_advisor_ids(store, scope_type, scope_id)

    recommendation_ids: list[str] = []
    for advisor_id in advisor_ids:
        recommendation_ids.extend(store.in_ids("phx_dm_recommendation_for_advisor", advisor_id))

    adoption: dict[str, dict] = {}
    feedback_summary: dict[str, dict] = {}
    total_reward = 0.0
    total_score_delta = 0.0
    feedback_ids: list[str] = []
    outcome_ids: list[str] = []
    learning_ids: list[str] = []

    for rec_id in recommendation_ids:
        attrs = store.vertex("phx_dm_recommendation", rec_id) or {}
        status = str(attrs.get("status"))
        bucket = adoption.setdefault(
            status, {"recommendation_status": status, "recommendation_count": 0, "estimated_impact": 0.0}
        )
        bucket["recommendation_count"] += 1
        bucket["estimated_impact"] += float(attrs.get("estimated_impact") or 0)
        for feedback_id in store.in_ids("phx_dm_feedback_for_recommendation", rec_id):
            feedback_ids.append(feedback_id)
            f_attrs = store.vertex("phx_dm_feedback_event", feedback_id) or {}
            action = str(f_attrs.get("action") or f_attrs.get("feedback_action"))
            f_bucket = feedback_summary.setdefault(action, {"feedback_action": action, "feedback_count": 0})
            f_bucket["feedback_count"] += 1
            total_reward += float(f_attrs.get("reward_score") or 0)
            for outcome_id in store.in_ids("phx_dm_outcome_for_feedback", feedback_id):
                outcome_ids.append(outcome_id)
                for learning_id in store.in_ids("phx_dm_learning_from_outcome", outcome_id):
                    learning_ids.append(learning_id)
                    l_attrs = store.vertex("phx_dm_learning_signal", learning_id) or {}
                    total_score_delta += float(l_attrs.get("ranking_weight_delta") or l_attrs.get("score_delta") or 0)

    return [
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "recommendation_adoption": list(adoption.values()),
            "feedback_summary": list(feedback_summary.values()),
            "total_reward": round(total_reward, 4),
            "total_score_delta": round(total_score_delta, 4),
            "recommendations": vset(store, "phx_dm_recommendation", recommendation_ids),
            "feedback": vset(store, "phx_dm_feedback_event", feedback_ids),
            "outcomes": vset(store, "phx_dm_outcome_event", outcome_ids),
            "learning": vset(store, "phx_dm_learning_signal", learning_ids),
        }
    ]


@mock_query("get_embeddings_by_type")
def get_embeddings_by_type(store: FoundationGraphStore, params: dict) -> list[dict]:
    """GQ-054 mock — every embedding vertex for one entity type plus that type's
    display vertices (exactly one of households/accounts/advisors non-empty), in
    the real vset row shape, mirroring the GSQL's exact-match filter + ORDER BY."""
    entity_type = str(params.get("entity_type") or "")
    embedding_ids = sorted(
        (
            emb_id
            for emb_id, attrs in store.all_vertices("phx_dm_embedding").items()
            if str(attrs.get("entity_type", "")) == entity_type
        ),
        key=lambda emb_id: str((store.vertex("phx_dm_embedding", emb_id) or {}).get("entity_id") or ""),
    )
    return [
        {
            "entity_type": entity_type,
            "embeddings": vset(store, "phx_dm_embedding", embedding_ids),
            "households": vset(
                store, "phx_dm_household", store.all_vertices("phx_dm_household") if entity_type == "HOUSEHOLD" else []
            ),
            "accounts": vset(
                store, "phx_dm_account", store.all_vertices("phx_dm_account") if entity_type == "ACCOUNT" else []
            ),
            "advisors": vset(
                store, "phx_dm_advisor", store.all_vertices("phx_dm_advisor") if entity_type == "ADVISOR" else []
            ),
        }
    ]


@mock_query("get_playbooks")
def get_playbooks(store: FoundationGraphStore, params: dict) -> list[dict]:
    """GQ-059 mock — full phx_dm_playbook listing ordered by playbook_id."""
    playbook_ids = sorted(store.all_vertices("phx_dm_playbook").keys())
    return [{"playbooks": vset(store, "phx_dm_playbook", playbook_ids)}]


@mock_query("get_recommendation_advisor")
def get_recommendation_advisor(store: FoundationGraphStore, params: dict) -> list[dict]:
    """GQ-060 mock — the advisor a recommendation points at via
    phx_dm_recommendation_for_advisor."""
    recommendation_id = str(params.get("recommendation_id") or "")
    advisor_ids = store.out_ids("phx_dm_recommendation_for_advisor", recommendation_id)
    return [
        {
            "recommendation_id": recommendation_id,
            "advisor": vset(store, "phx_dm_advisor", advisor_ids),
        }
    ]


@mock_query("get_recommendation_status_counts")
def get_recommendation_status_counts(store: FoundationGraphStore, params: dict) -> list[dict]:
    """GQ-061 mock — per-status counts over ALL recommendation vertices
    (MapAccum print shape), household-level recs included."""
    counts: dict[str, int] = {}
    for attrs in store.all_vertices("phx_dm_recommendation").values():
        status = str(attrs.get("status") or "")
        counts[status] = counts.get(status, 0) + 1
    return [{"status_counts": counts}]
