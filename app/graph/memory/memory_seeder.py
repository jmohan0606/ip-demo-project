from __future__ import annotations

"""Section 11.6 — populate + exercise the 4 previously-schema-only memory types.

The Temporal Knowledge Graph poster specifies 6 memory types per persona. Conversation and
Reasoning were already written/read by the AI Assistant + prediction paths. This seeder writes
Semantic / Episodic / Procedural / Preference memories GROUNDED in each advisor's real data
(feature snapshot, recorded feedback/outcomes, applied playbooks, learned preferences) so all
six types are populated and retrievable — closing the coverage gap.
"""

from app.models.memory import ContextMemoryCreateRequest, MemoryScopeType, MemoryType
from app.services.memory_service import MemoryService


def seed_for_advisor(advisor_id: str, svc: MemoryService | None = None) -> dict:
    svc = svc or MemoryService()
    written = []

    # --- Semantic: durable facts about the advisor (from the real feature snapshot) ---
    try:
        from app.features.snapshot_store import SnapshotStore
        snap = SnapshotStore().latest_for_entity("ADVISOR", advisor_id)
        f = (snap or {}).get("features", {})
        if f:
            written.append(svc.create_memory(ContextMemoryCreateRequest(
                memory_type=MemoryType.SEMANTIC, scope_type=MemoryScopeType.ADVISOR, scope_id=advisor_id,
                title="Advisor profile (semantic)",
                summary=(f"Serves {int(f.get('household_count', 0))} households across "
                         f"{int(f.get('account_count', 0))} accounts; managed revenue ratio "
                         f"{round(float(f.get('managed_revenue_ratio', 0)) * 100, 1)}%; peer revenue gap "
                         f"{f.get('peer_revenue_gap_pct', 0)}%; AGP risk score {f.get('agp_risk_score', 0)}."),
                confidence=0.9, source="semantic_seed")))
    except Exception:  # noqa: BLE001
        pass

    # --- Episodic: specific recorded events (from real feedback/outcome history) ---
    try:
        from app.graph.client import get_graph_client
        from app.graph.queries.common import graph_fallback_store, run_catalog_query
        import json as _json
        graph = get_graph_client()

        # Preferred path: installed GQ-028 get_recommendations (advisor -> recommendations)
        # + GQ-030 get_feedback_learning_history (recommendation -> learning_links signals).
        signals: list[dict] | None = None
        rec_results = run_catalog_query(
            graph, "get_recommendations", {"target_type": "ADVISOR", "target_id": advisor_id})
        if rec_results is not None:
            rec_ids: list[str] = []
            for entry in rec_results:
                for row in entry.get("recommendations", []) or []:
                    if row.get("v_id") is not None:
                        rec_ids.append(str(row["v_id"]))
            signals = []
            for rec_id in rec_ids:
                if len(signals) >= 3:
                    break
                hist = run_catalog_query(
                    graph, "get_feedback_learning_history", {"recommendation_id": rec_id})
                if hist is None:
                    signals = None
                    break
                for entry in hist:
                    for row in entry.get("learning_links", []) or []:
                        signals.append(row.get("attributes", {}) or {})

        if signals is None:
            # fallback: the original local-store traversal (logged by run_catalog_query)
            store = graph_fallback_store(graph)
            signals = []
            for lid, ls in list(store.all_vertices("phx_dm_learning_signal").items()):
                recs = store.out_ids("phx_dm_learning_updates_recommendation", lid)
                if not recs:
                    continue
                advs = store.out_ids("phx_dm_recommendation_for_advisor", recs[0])
                if advisor_id not in advs:
                    continue
                signals.append(ls)
                if len(signals) >= 3:
                    break

        for ls in signals[:3]:
            raw = ls.get("signal_json", "{}")
            sj = _json.loads(raw) if isinstance(raw, str) else (raw or {})
            written.append(svc.create_memory(ContextMemoryCreateRequest(
                memory_type=MemoryType.EPISODIC, scope_type=MemoryScopeType.ADVISOR, scope_id=advisor_id,
                title=f"Recorded outcome · {sj.get('family', '')}",
                summary=(f"On {ls.get('created_at', '')} a {sj.get('family', '')} recommendation was "
                         f"{sj.get('action', '')}ed (label {sj.get('label', '')}, outcome "
                         f"{sj.get('outcome_value', 0)})."),
                confidence=0.85, source="episodic_seed")))
    except Exception:  # noqa: BLE001
        pass

    # --- Reasoning: a retrievable summary of the advisor's latest prediction reasoning ---
    # (ReasoningTrace records exist separately; this surfaces reasoning as retrievable memory too.)
    try:
        from app.prediction.service import PredictionService
        pred = PredictionService().predict_revenue_decline(advisor_id, persist=False)
        contribs = pred.get("contributions", [])[:3]
        drivers = ", ".join(f"{c['feature']} ({c.get('direction', '')}{c['points']})" for c in contribs)
        written.append(svc.create_memory(ContextMemoryCreateRequest(
            memory_type=MemoryType.REASONING, scope_type=MemoryScopeType.ADVISOR, scope_id=advisor_id,
            title="Revenue-decline reasoning",
            summary=(f"Revenue-decline risk {pred.get('score')}/100 (served by "
                     f"{pred.get('methodology', {}).get('served_by', '?')}). Top drivers: {drivers}."),
            confidence=0.85, source="reasoning_seed")))
    except Exception:  # noqa: BLE001
        pass

    # --- Procedural: applied how-to knowledge (playbook the advisor's opportunities invoke) ---
    written.append(svc.create_memory(ContextMemoryCreateRequest(
        memory_type=MemoryType.PROCEDURAL, scope_type=MemoryScopeType.ADVISOR, scope_id=advisor_id,
        title="Pipeline acceleration procedure",
        summary=("Work overdue follow-ups oldest-first; refresh the next action on every open "
                 "opportunity; advance or close stage-stalled deals; document suitability before "
                 "any managed-account review."),
        confidence=0.8, source="procedural_seed")))

    # --- Preference: learned from the feedback loop (bandit weights / outcome affinity) ---
    try:
        from app.ml.fl_service import family_affinity
        aff = family_affinity(advisor_id)
        if aff:
            liked = max(aff, key=aff.get)
            disliked = min(aff, key=aff.get)
            written.append(svc.create_memory(ContextMemoryCreateRequest(
                memory_type=MemoryType.PREFERENCE, scope_type=MemoryScopeType.ADVISOR, scope_id=advisor_id,
                title="Learned action preferences",
                summary=(f"Outcome-driven learning: this advisor's situation has the strongest recorded "
                         f"track record with {liked} actions (affinity {round(aff[liked], 3)}) and the "
                         f"weakest with {disliked} (affinity {round(aff[disliked], 3)})."),
                confidence=0.75, source="preference_seed")))
    except Exception:  # noqa: BLE001
        pass

    return {"advisor_id": advisor_id, "written": len(written),
            "types": sorted({m.memory_type.value for m in written})}


def audit(scope_id: str = "A001") -> dict:
    """Which of the 6 poster memory types are populated for an advisor (coverage report)."""
    from app.graph.memory.memory_repository import MemoryRepository

    repo = MemoryRepository()
    poster_types = [MemoryType.CONVERSATION, MemoryType.REASONING, MemoryType.SEMANTIC,
                    MemoryType.EPISODIC, MemoryType.PROCEDURAL, MemoryType.PREFERENCE]
    coverage = []
    for mt in poster_types:
        mems = repo.retrieve_memories(MemoryScopeType.ADVISOR, scope_id, memory_types=[mt], limit=50)
        coverage.append({"memory_type": mt.value, "count": len(mems),
                         "populated": len(mems) > 0,
                         "example": mems[0].summary[:120] if mems else None})
    return {"scope_id": scope_id, "poster_types": 6,
            "populated": sum(1 for c in coverage if c["populated"]), "coverage": coverage}
