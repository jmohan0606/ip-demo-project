from __future__ import annotations

from app.models.feedback_learning import FeedbackAction, FeedbackEventRecord, LearningSignalRecord, LearningSignalType, OutcomeEventRecord
from app.shared.ids import timestamp_id


class LearningSignalEngine:
    def create_signal(self, feedback: FeedbackEventRecord, outcome: OutcomeEventRecord | None) -> LearningSignalRecord:
        if feedback.action == FeedbackAction.REJECT:
            signal_type = LearningSignalType.ADVISOR_PREFERENCE
            summary = "Negative advisor feedback should reduce similar recommendation ranking."
            delta = -0.08
        elif feedback.action == FeedbackAction.COMPLETE:
            signal_type = LearningSignalType.RECOMMENDATION_REWARD
            summary = "Completed recommendation with outcome should increase similar recommendation ranking."
            delta = 0.12
        elif feedback.action == FeedbackAction.ACCEPT:
            signal_type = LearningSignalType.RECOMMENDATION_REWARD
            summary = "Accepted recommendation should slightly increase similar recommendation ranking."
            delta = 0.06
        elif feedback.action == FeedbackAction.MODIFY:
            signal_type = LearningSignalType.ADVISOR_PREFERENCE
            summary = "Modified recommendation indicates preference learning for future wording/action."
            delta = 0.02
        else:
            signal_type = LearningSignalType.OPPORTUNITY_RANKING
            summary = "Ignored recommendation should slightly reduce urgency ranking."
            delta = -0.02

        if outcome:
            summary += f" Outcome observed: {outcome.outcome_type.value}, value={outcome.outcome_value}."

        return LearningSignalRecord(
            learning_signal_id=timestamp_id("learn"),
            feedback_id=feedback.feedback_id,
            recommendation_id=feedback.recommendation_id,
            outcome_id=outcome.outcome_id if outcome else None,
            signal_type=signal_type,
            signal_value=feedback.reward_score,
            signal_summary=summary,
            ranking_weight_delta=delta,
            memory_update_summary=f"Feedback learning signal captured for recommendation {feedback.recommendation_id}.",
        )
