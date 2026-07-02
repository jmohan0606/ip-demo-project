from __future__ import annotations

from uuid import uuid4

from app.recommendations.models import FeedbackEvent


class LearningEngine:
    def score_delta_for_action(self, action: str) -> float:
        return {
            "accept": 0.08,
            "complete": 0.12,
            "modify": 0.03,
            "ignore": -0.02,
            "reject": -0.07,
        }.get(action, 0.0)

    def create_feedback(self, recommendation_id: str, action: str, notes: str = "") -> FeedbackEvent:
        delta = self.score_delta_for_action(action)
        if action in {"accept", "complete"}:
            signal = "Positive reinforcement signal captured."
            memory = "Increase ranking weight for similar opportunity/recommendation patterns."
        elif action == "modify":
            signal = "Modification signal captured."
            memory = "Store advisor preference and adjust future wording/actions."
        elif action == "ignore":
            signal = "Weak negative signal captured."
            memory = "Reduce urgency but keep opportunity pattern available."
        else:
            signal = "Negative reinforcement signal captured."
            memory = "Reduce ranking weight for similar recommendations unless context changes."

        return FeedbackEvent(
            feedback_id=f"FDB-{uuid4().hex[:10].upper()}",
            recommendation_id=recommendation_id,
            action=action,
            notes=notes,
            learning_signal=signal,
            score_delta=delta,
            memory_update=memory,
        )
