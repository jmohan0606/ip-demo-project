from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

from app.graph.artifacts import upsert_edge, upsert_vertex
from app.graph.client import GraphClient, get_graph_client
from app.recommendations.service import LearningWeightStore

# Reward and ranking-weight delta per feedback action (the RL-style signal).
ACTION_SIGNALS = {
    "ACCEPT": {"reward": 0.6, "delta": 0.05, "summary": "Positive signal: raise ranking for this action family."},
    "COMPLETE": {"reward": 1.0, "delta": 0.10, "summary": "Strong positive signal: completed action with outcome."},
    "MODIFY": {"reward": 0.3, "delta": 0.02, "summary": "Preference signal: keep family, adjust wording/actions."},
    "IGNORE": {"reward": -0.1, "delta": -0.02, "summary": "Weak negative signal: reduce urgency for this family."},
    "REJECT": {"reward": -0.5, "delta": -0.08, "summary": "Negative signal: lower ranking for this action family."},
}


class FeedbackLearningService:
    """Closes the loop (spec Section 13, feedback learning): a feedback action
    persists feedback -> outcome -> learning-signal artifacts in the graph AND
    moves the action-family learning weight that RecommendationService reads at
    ranking time — so the next generation run visibly re-ranks."""

    def __init__(self, graph: GraphClient | None = None, as_of: date | None = None) -> None:
        self.graph = graph or get_graph_client()
        self.as_of = as_of or date(2026, 7, 3)
        self.learning = LearningWeightStore()

    def submit(
        self,
        recommendation_id: str,
        action: str,
        action_family: str,
        user_id: str = "U_ADV001",
        reason_text: str = "",
        outcome_value: float | None = None,
    ) -> dict:
        action = action.upper()
        signal = ACTION_SIGNALS.get(action)
        if signal is None:
            raise ValueError(f"Unknown feedback action '{action}' (expected {sorted(ACTION_SIGNALS)})")

        suffix = uuid4().hex[:8].upper()
        feedback_id = f"FB_{suffix}"
        upsert_vertex(self.graph, "phx_dm_feedback_event", "feedback_id", {
            "feedback_id": feedback_id,
            "action": action,
            "reason_code": "USER_FEEDBACK",
            "reason_text": reason_text or f"{action.title()} via feedback API",
            "created_at": self.as_of.isoformat(),
            "user_id": user_id,
        })
        upsert_edge(self.graph, "phx_dm_feedback_for_recommendation", "phx_dm_feedback_event",
                    "phx_dm_recommendation", feedback_id, recommendation_id)

        outcome_id = None
        if action in {"COMPLETE", "ACCEPT"} or outcome_value is not None:
            outcome_id = f"OUT_{suffix}"
            upsert_vertex(self.graph, "phx_dm_outcome_event", "outcome_id", {
                "outcome_id": outcome_id,
                "outcome_type": "REVENUE_IMPACT" if outcome_value else "ACTION_TAKEN",
                "outcome_value": outcome_value or 0,
                "outcome_unit": "USD",
                "observed_at": self.as_of.isoformat(),
                "notes": f"Outcome recorded from {action} feedback.",
            })
            upsert_edge(self.graph, "phx_dm_outcome_for_feedback", "phx_dm_outcome_event",
                        "phx_dm_feedback_event", outcome_id, feedback_id)

        new_weight = self.learning.apply_delta(action_family, signal["delta"], self.as_of.isoformat())
        learning_signal_id = f"LS_{suffix}"
        upsert_vertex(self.graph, "phx_dm_learning_signal", "learning_signal_id", {
            "learning_signal_id": learning_signal_id,
            "signal_type": "RECOMMENDATION_FEEDBACK",
            "reward": signal["reward"],
            "score_delta": signal["delta"],
            "signal_json": json.dumps({
                "action": action,
                "family": action_family,
                "new_family_weight": new_weight,
                "summary": signal["summary"],
            }),
            "created_at": self.as_of.isoformat(),
        })
        if outcome_id:
            upsert_edge(self.graph, "phx_dm_learning_from_outcome", "phx_dm_learning_signal",
                        "phx_dm_outcome_event", learning_signal_id, outcome_id)
        upsert_edge(self.graph, "phx_dm_learning_updates_recommendation", "phx_dm_learning_signal",
                    "phx_dm_recommendation", learning_signal_id, recommendation_id)

        return {
            "feedback_id": feedback_id,
            "outcome_id": outcome_id,
            "learning_signal_id": learning_signal_id,
            "action": action,
            "action_family": action_family,
            "reward": signal["reward"],
            "ranking_weight_delta": signal["delta"],
            "new_family_weight": new_weight,
            "effect": (
                f"Future '{action_family}' recommendations rank with weight {new_weight} "
                f"(was {round(new_weight - signal['delta'], 4)})."
            ),
        }

    def learning_state(self) -> dict:
        return {"weights": self.learning.all_weights(), "signals": ACTION_SIGNALS}
