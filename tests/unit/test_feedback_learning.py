from app.feedback.reward_engine import FeedbackRewardEngine
from app.models.feedback_learning import FeedbackAction, OutcomeType


def test_feedback_reward():
    engine = FeedbackRewardEngine()
    reward = engine.reward(FeedbackAction.ACCEPT, OutcomeType.REVENUE_IMPACT, 50000)
    assert reward > 0
