from __future__ import annotations

from app.models.feedback_learning import FeedbackAction, OutcomeType


class FeedbackRewardEngine:
    def base_reward(self, action: FeedbackAction) -> float:
        if action == FeedbackAction.ACCEPT:
            return 0.70
        if action == FeedbackAction.COMPLETE:
            return 0.90
        if action == FeedbackAction.MODIFY:
            return 0.45
        if action == FeedbackAction.IGNORE:
            return 0.05
        if action == FeedbackAction.REJECT:
            return -0.35
        return 0.0

    def outcome_adjustment(self, outcome_type: OutcomeType | None, outcome_value: float | None) -> float:
        if outcome_type is None:
            return 0.0
        value = outcome_value or 0.0
        if outcome_type in {OutcomeType.REVENUE_IMPACT, OutcomeType.NNM_IMPACT, OutcomeType.AUM_IMPACT}:
            if value > 50000:
                return 0.20
            if value > 0:
                return 0.10
            if value < 0:
                return -0.20
        if outcome_type in {OutcomeType.MEETING_SCHEDULED, OutcomeType.CLIENT_ENGAGED, OutcomeType.PRODUCT_REVIEW_COMPLETED}:
            return 0.08
        if outcome_type == OutcomeType.NO_IMPACT:
            return -0.05
        return 0.0

    def reward(self, action: FeedbackAction, outcome_type: OutcomeType | None = None, outcome_value: float | None = None) -> float:
        score = self.base_reward(action) + self.outcome_adjustment(outcome_type, outcome_value)
        return round(max(-1.0, min(1.0, score)), 4)
