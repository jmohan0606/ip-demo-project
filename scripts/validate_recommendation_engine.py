from __future__ import annotations

from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.recommendation_service import RecommendationService


def main() -> None:
    service = RecommendationService()
    result = service.run_recommendations(RecommendationRunRequest(write_to_tigergraph=False, limit=200))
    assert result.recommendations_created > 0
    rows = service.list_recommendations(RecommendationSearchRequest(limit=20))
    assert len(rows) > 0
    assert "evidence" in rows[0]
    assert "reasoning_steps" in rows[0]
    counts = service.counts()
    assert len(counts) > 0
    print("Recommendation Engine validation passed.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
