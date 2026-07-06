from __future__ import annotations

"""Section 11.3 §5 — outcome-driven-learning read services (before/after demo, affinity).

No heavy ML imports — reads the persisted -ft embeddings (via VectorClient) + the affinity
table + the registry. The fine-tune itself lives in fl_finetune.py.
"""

import sqlite3

from app.config.settings import get_settings
from app.ml import registry


def _db() -> str:
    return get_settings().sqlite_db_path


def _affinity(advisor_id: str, model_name: str) -> dict[str, float]:
    try:
        with sqlite3.connect(_db()) as conn:
            rows = conn.execute(
                "SELECT family, affinity FROM fl_family_affinity WHERE advisor_id=? AND model_name=?",
                (advisor_id, model_name)).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {f: a for f, a in rows}


def family_affinity(advisor_id: str, model_name: str | None = None) -> dict[str, float]:
    """Per-family outcome affinity for an advisor under the active (or given) model."""
    return _affinity(advisor_id, model_name or registry.active_embedding_model())


def outcome_learning_state() -> dict:
    ft = registry.get_entry("graphsage-v1-ft")
    return {
        "active_model": registry.active_embedding_model(),
        "fine_tuned_available": bool(ft),
        "gate": ft.get("quality_gate") if ft else None,
        "events_used": ft.get("events_used") if ft else 0,
        "last_retrain": ft.get("training_date") if ft else None,
        "metrics": ft.get("metrics") if ft else None,
    }


def before_after(advisor_id: str, top_k: int = 5) -> dict:
    """The before/after demo payload: similar advisors + affinity under v1 vs -ft."""
    ft = registry.get_entry("graphsage-v1-ft")
    if not ft:
        return {"available": False, "advisor_id": advisor_id,
                "hint": "Run POST /feedback-learning/retrain to fine-tune on recorded outcomes."}
    from app.ml.vector_client import get_vector_client

    vc = get_vector_client()

    def _similar(model: str) -> list[dict]:
        vec = vc.get("ADVISOR", advisor_id, model_name=model)
        if vec is None:
            return []
        return vc.search("ADVISOR", vec, top_k, exclude_id=advisor_id, model_name=model)

    before = _similar("graphsage-v1")
    after = _similar("graphsage-v1-ft")
    rank_before = {m["entity_id"]: i for i, m in enumerate(before)}
    rank_after = {m["entity_id"]: i for i, m in enumerate(after)}
    moves = []
    for i, m in enumerate(after):
        eid = m["entity_id"]
        prev = rank_before.get(eid)
        moves.append({"entity_id": eid, "after_rank": i, "before_rank": prev,
                      "move": ("new" if prev is None else prev - i)})

    aff_before = _affinity(advisor_id, "graphsage-v1")
    aff_after = _affinity(advisor_id, "graphsage-v1-ft")
    families = sorted(set(aff_before) | set(aff_after))
    affinity = [{"family": f, "before": aff_before.get(f), "after": aff_after.get(f),
                 "delta": round((aff_after.get(f, 0) - aff_before.get(f, 0)), 4)} for f in families]

    metrics = ft.get("metrics", {})
    return {
        "available": True, "advisor_id": advisor_id,
        "similar_before": before, "similar_after": after, "rank_moves": moves,
        "affinity": affinity,
        "separation": {"overall_before": metrics.get("separation_before"),
                       "overall_after": metrics.get("separation_after"),
                       "per_family": metrics.get("per_family_separation")},
        "link_pred_auc": {"before": metrics.get("link_pred_auc_before"),
                          "after": metrics.get("link_pred_auc_after")},
        "model_versions": {"before": "graphsage-v1", "after": ft.get("served_by")},
        "events_used": ft.get("events_used"),
    }
