from __future__ import annotations

import json

from app.graph.artifacts import upsert_edge, upsert_vertex
from app.graph.client import get_graph_client
from app.shared.ids import new_id

# Selectable coaching-task templates the manager can assign (CLAUDE.md 9.5).
TASK_CATALOG = [
    {"title": "Complete overdue lead follow-ups", "category": "CRM_EXECUTION",
     "instruction": "Work the overdue lead queue to zero this week and log next actions in CRM.", "priority": "HIGH"},
    {"title": "Run a prospecting sprint", "category": "PROSPECTING",
     "instruction": "Book 5 new prospect meetings from the referral and centre-of-influence pipeline.", "priority": "MEDIUM"},
    {"title": "Deepen managed-account penetration", "category": "PRODUCT_REVIEW",
     "instruction": "Review top-10 households for suitable managed-account conversions; document rationale.", "priority": "MEDIUM"},
    {"title": "Re-engage at-risk households", "category": "CLIENT_ENGAGEMENT",
     "instruction": "Schedule reviews with households showing declining engagement or negative NCF.", "priority": "HIGH"},
    {"title": "Close the current AGP milestone gap", "category": "AGP_MILESTONE",
     "instruction": "Build a concrete plan to reach 100% attainment before the next milestone due date.", "priority": "HIGH"},
    {"title": "Improve referral conversion", "category": "PROSPECTING",
     "instruction": "Follow up all open referrals within 48h and advance each to a next step.", "priority": "MEDIUM"},
]


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
        self._graph = get_graph_client()
        self._store = self._graph.store

    def _name(self, advisor_id: str) -> str:
        return str((self._store.vertex("phx_dm_advisor", advisor_id) or {}).get("advisor_name") or advisor_id)

    def _user(self, user_id: str | None) -> dict:
        if not user_id:
            return {"user_id": None, "display_name": None, "role_code": None}
        u = self._store.vertex("phx_dm_persona_user", user_id) or {}
        return {
            "user_id": user_id,
            "display_name": u.get("display_name") or user_id,
            "role_code": u.get("role_code"),
        }

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
                "coach": self._user(a.get("coach_user_id")),
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
                "reviewer": self._user(a.get("reviewer_user_id")),
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

    # -- Manager-assigned coaching tasks (CLAUDE.md 9.5): real CRUD persisted to the
    #    graph, retrievable with status, and read back into the AI context. --

    def task_catalog(self) -> list[dict]:
        return TASK_CATALOG

    def tasks(self, advisor_id: str) -> dict:
        store = self._store
        rows = []
        for tid in store.in_ids("phx_dm_coaching_task_for_advisor", advisor_id):
            a = store.vertex("phx_dm_coaching_task", tid) or {}
            assigned = store.out_ids("phx_dm_coaching_task_assigned_by", tid)
            rows.append({
                "task_id": a.get("task_id", tid),
                "title": a.get("title"),
                "category": a.get("category"),
                "instruction": a.get("instruction"),
                "status": a.get("status", "OPEN"),
                "priority": a.get("priority"),
                "created_date": a.get("created_date"),
                "due_date": a.get("due_date"),
                "completed_date": a.get("completed_date"),
                "assigned_by": self._user(assigned[0] if assigned else a.get("created_by_user_id")),
            })
        rows.sort(key=lambda r: str(r.get("created_date") or ""), reverse=True)
        open_count = sum(1 for r in rows if str(r["status"]).upper() != "COMPLETED")
        return {"advisor_id": advisor_id, "tasks": rows, "open_count": open_count, "total": len(rows)}

    def create_task(
        self, advisor_id: str, title: str, category: str, instruction: str,
        priority: str = "MEDIUM", due_date: str | None = None,
        created_by_user_id: str = "U_MDW01", created_date: str | None = None,
    ) -> dict:
        """Persist a new coaching task and wire it to the advisor + assigning manager.
        Written through the GraphClient adapter (mock upsert writes the same indexes
        the read path traverses), so it is immediately retrievable and visible to AI."""
        task_id = new_id("CTASKU")
        record = {
            "task_id": task_id,
            "title": title,
            "category": category,
            "instruction": instruction,
            "status": "OPEN",
            "priority": priority,
            "created_date": created_date,
            "due_date": due_date,
            "completed_date": None,
            "created_by_user_id": created_by_user_id,
        }
        upsert_vertex(self._graph, "phx_dm_coaching_task", "task_id", record)
        upsert_edge(self._graph, "phx_dm_coaching_task_for_advisor",
                    "phx_dm_coaching_task", "phx_dm_advisor", task_id, advisor_id)
        upsert_edge(self._graph, "phx_dm_coaching_task_assigned_by",
                    "phx_dm_coaching_task", "phx_dm_persona_user", task_id, created_by_user_id)
        return {"created": True, "task_id": task_id, "advisor_id": advisor_id, **record}

    def update_task_status(self, task_id: str, status: str, completed_date: str | None = None) -> dict:
        existing = self._store.vertex("phx_dm_coaching_task", task_id) or {}
        if not existing:
            return {"updated": False, "task_id": task_id, "error": "not found"}
        record = {**existing, "task_id": task_id, "status": status.upper()}
        if status.upper() == "COMPLETED":
            record["completed_date"] = completed_date
        upsert_vertex(self._graph, "phx_dm_coaching_task", "task_id", record)
        return {"updated": True, "task_id": task_id, "status": status.upper()}

    def open_tasks_for_context(self, advisor_id: str) -> list[dict]:
        """The AI read path: open manager-assigned tasks surfaced to the AI Assistant
        / recommendation context so coaching instructions actually steer the AI."""
        return [
            {"title": t["title"], "category": t["category"], "instruction": t["instruction"],
             "priority": t["priority"], "assigned_by": (t["assigned_by"] or {}).get("display_name")}
            for t in self.tasks(advisor_id)["tasks"]
            if str(t["status"]).upper() != "COMPLETED"
        ]
