from app.models.recommendations import RecommendationRunRequest
from app.services.recommendation_service import RecommendationService


def test_recommendation_run():
    result = RecommendationService().run_recommendations(
        RecommendationRunRequest(write_to_tigergraph=False, limit=50)
    )
    assert result.recommendations_created > 0
