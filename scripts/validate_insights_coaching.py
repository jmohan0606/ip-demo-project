from __future__ import annotations

from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.predictions import PredictionRunRequest
from app.models.recommendations import RecommendationRunRequest
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService


def main() -> None:
    # Ensure downstream engines have data
    PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
    RecommendationService().run_recommendations(RecommendationRunRequest(write_to_tigergraph=False, limit=100))

    service = InsightsCoachingService()
    payload = service.generate_dashboard_payload(
        InsightRequest(
            scope_type=InsightScopeType.ADVISOR,
            scope_id="ADV0001",
            persona="Advisor",
            time_period="YTD",
            question="What should I focus on this week?",
            write_to_tigergraph=False,
        )
    )
    assert payload.cards
    assert payload.coaching_plan is not None
    assert payload.executive_summary
    print("AI Insights & Coaching validation passed.")
    print(f"Cards: {len(payload.cards)}")
    print(payload.executive_summary)


if __name__ == "__main__":
    main()
