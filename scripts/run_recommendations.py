from __future__ import annotations

from app.models.recommendations import RecommendationRunRequest
from app.services.recommendation_service import RecommendationService


def main() -> None:
    result = RecommendationService().run_recommendations(RecommendationRunRequest(write_to_tigergraph=False))
    print("Recommendation run complete.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
