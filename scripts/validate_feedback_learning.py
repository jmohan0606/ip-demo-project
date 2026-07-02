from __future__ import annotations

from app.models.feedback_learning import FeedbackAction, FeedbackActor, FeedbackSearchRequest, FeedbackSubmitRequest, OutcomeType
from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.feedback_learning_service import FeedbackLearningService
from app.services.recommendation_service import RecommendationService


def main() -> None:
    rec_service = RecommendationService()
    rec_service.run_recommendations(RecommendationRunRequest(write_to_tigergraph=False, limit=50))
    recs = rec_service.list_recommendations(RecommendationSearchRequest(limit=1))
    assert recs, "No recommendations generated for feedback validation."

    feedback_service = FeedbackLearningService()
    result = feedback_service.submit_feedback(
        FeedbackSubmitRequest(
            recommendation_id=recs[0]["recommendation_id"],
            actor=FeedbackActor.ADVISOR,
            action=FeedbackAction.ACCEPT,
            reason="Validation accepted recommendation.",
            outcome_type=OutcomeType.REVENUE_IMPACT,
            outcome_value=50000,
            outcome_summary="Validation revenue impact.",
            write_to_tigergraph=False,
        )
    )
    assert result.feedback.feedback_id
    assert result.learning_signal.learning_signal_id
    rows = feedback_service.list_feedback(FeedbackSearchRequest(limit=10))
    assert rows
    print("Feedback Learning validation passed.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
