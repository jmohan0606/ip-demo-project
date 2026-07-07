"""Graph-traversal reads for durable state migrated onto the StateRepository:
learning weights, impact-ledger entries, and recommendation status-transitions.

Mock equivalents of the GQ-### GSQL queries (docs/tigergraph_foundation/tigergraph/
queries/GQ-044..046). Registered in MOCK_QUERY_IMPLS via @mock_query so the TigerGraph
tier's reads work identically in mock mode and (via the installed GSQL) in real mode.
"""

from __future__ import annotations

from app.graph.client import mock_query
from app.graph.foundation_store import FoundationGraphStore


@mock_query("get_learning_weights")
def get_learning_weights(store: FoundationGraphStore, params: dict) -> list[dict]:
    """All learning-weight vertices (optionally one family) — the RL/bandit weights."""
    family = str(params.get("family") or "")
    rows = []
    for vid, attrs in store.all_vertices("phx_dm_learning_weight").items():
        if family and str(attrs.get("family") or vid) != family:
            continue
        rows.append({"family": attrs.get("family") or vid,
                     "weight": attrs.get("weight"),
                     "feedback_count": attrs.get("feedback_count"),
                     "updated_at": attrs.get("updated_at")})
    rows.sort(key=lambda r: str(r["family"]))
    return rows


@mock_query("get_impact_ledger")
def get_impact_ledger(store: FoundationGraphStore, params: dict) -> list[dict]:
    """Impact-ledger entries by graph traversal. Filter by advisor (via
    phx_dm_impact_for_advisor edge) or recommendation (phx_dm_impact_from_recommendation),
    else all. Newest first by created_ts."""
    advisor_id = str(params.get("advisor_id") or "")
    recommendation_id = str(params.get("recommendation_id") or "")

    if advisor_id:
        ledger_ids = store.in_ids("phx_dm_impact_for_advisor", advisor_id)
    elif recommendation_id:
        ledger_ids = store.in_ids("phx_dm_impact_from_recommendation", recommendation_id)
    else:
        ledger_ids = list(store.all_vertices("phx_dm_impact_ledger").keys())

    rows = []
    for lid in ledger_ids:
        attrs = store.vertex("phx_dm_impact_ledger", lid)
        if attrs:
            rows.append({"ledger_id": lid, **attrs})
    rows.sort(key=lambda r: str(r.get("created_ts") or ""), reverse=True)
    return rows


@mock_query("get_rec_status_transitions")
def get_rec_status_transitions(store: FoundationGraphStore, params: dict) -> list[dict]:
    """Status-transition history for a recommendation, by traversing
    phx_dm_transition_of_recommendation. Oldest first (chronological audit trail)."""
    recommendation_id = str(params.get("recommendation_id") or "")
    transition_ids = store.in_ids("phx_dm_transition_of_recommendation", recommendation_id)
    rows = []
    for tid in transition_ids:
        attrs = store.vertex("phx_dm_rec_status_transition", tid)
        if attrs:
            rows.append({"transition_id": tid, **attrs})
    rows.sort(key=lambda r: str(r.get("created_ts") or ""))
    return rows
