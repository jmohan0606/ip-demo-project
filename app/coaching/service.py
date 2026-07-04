from __future__ import annotations

import json

from app.graph.client import get_graph_client


def _parse_actions(raw) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw) if isinstance(raw, str) else raw
        return [str(x) for x in val] if isinstance(val, list) else [str(val)]
    except (json.JSONDecodeError, TypeError):
        return [str(raw)]


class CoachingReviewService:
    """Coaching sessions + manager reviews for an advisor, read straight from the
    graph (phx_dm_coaching_session / phx_dm_manager_review via *_for_advisor
    edges). Real records with real action items — the human side of the AGP loop."""

    def __init__(self) -> None:
        self._store = get_graph_client().store

    def _name(self, advisor_id: str) -> str:
        return str((self._store.vertex("phx_dm_advisor", advisor_id) or {}).get("advisor_name") or advisor_id)

    def advisor(self, advisor_id: str) -> dict:
        store = self._store
        sessions = []
        for sid in store.in_ids("phx_dm_coaching_for_advisor", advisor_id):
            a = store.vertex("phx_dm_coaching_session", sid) or {}
            sessions.append({
                "session_id": a.get("session_id", sid),
                "session_date": a.get("session_date"),
                "session_type": a.get("session_type"),
                "coach_user_id": a.get("coach_user_id"),
                "status": a.get("status"),
                "summary": a.get("summary"),
                "action_items": _parse_actions(a.get("action_items_json")),
                "next_session_date": a.get("next_session_date"),
            })
        sessions.sort(key=lambda s: str(s.get("session_date") or ""), reverse=True)

        reviews = []
        for rid in store.in_ids("phx_dm_review_for_advisor", advisor_id):
            a = store.vertex("phx_dm_manager_review", rid) or {}
            reviews.append({
                "review_id": a.get("review_id", rid),
                "review_date": a.get("review_date"),
                "review_type": a.get("review_type"),
                "reviewer_user_id": a.get("reviewer_user_id"),
                "rating": a.get("rating"),
                "status": a.get("status"),
                "summary": a.get("summary"),
            })
        reviews.sort(key=lambda r: str(r.get("review_date") or ""), reverse=True)

        ratings = [float(r["rating"]) for r in reviews if r.get("rating") is not None]
        open_actions = sum(len(s["action_items"]) for s in sessions if s.get("status") != "COMPLETED")
        return {
            "advisor_id": advisor_id,
            "advisor_name": self._name(advisor_id),
            "coaching_sessions": sessions,
            "manager_reviews": reviews,
            "summary": {
                "session_count": len(sessions),
                "review_count": len(reviews),
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                "open_action_items": open_actions,
                "total_action_items": sum(len(s["action_items"]) for s in sessions),
            },
            "evidence": {
                "source": "phx_dm_coaching_session + phx_dm_manager_review via *_for_advisor edges",
            },
        }
