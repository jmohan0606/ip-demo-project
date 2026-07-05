from __future__ import annotations

from app.models.recommendations import RecommendationActionRequest, RecommendationRunRequest, RecommendationRunResult, RecommendationSearchRequest
from app.recommendations.recommendation_repository import RecommendationRepository
from app.recommendations.service import RecommendationService as PipelineRecommendationService


class RecommendationService:
    def __init__(self) -> None:
        self.repo = RecommendationRepository()

    def run_recommendations(self, request: RecommendationRunRequest) -> RecommendationRunResult:
        # Delegate to the real Phase-8 pipeline, which detects opportunities via the real
        # OpportunityDetectionService and persists the full lineage chain (opportunity →
        # feature snapshot → playbook → learning-weighted priority). The legacy path here used
        # the dormant OpportunityService plus a clobbered RecommendationEngine whose signature
        # no longer matched — run_recommendations raised TypeError by construction.
        result = PipelineRecommendationService().generate_for_advisor(request.entity_id, persist=True)
        recommendations = result.get("recommendations", [])
        return RecommendationRunResult(
            recommendations_created=len(recommendations),
            status="completed",
            message=f"Generated {len(recommendations)} recommendations.",
        )

    def list_recommendations(self, request: RecommendationSearchRequest) -> list[dict]:
        return self.repo.list_recommendations(
            entity_id=request.entity_id,
            recommendation_type=request.recommendation_type.value if request.recommendation_type else None,
            status=request.status.value if request.status else None,
            limit=request.limit,
        )

    def update_status(self, request: RecommendationActionRequest) -> dict:
        self.repo.update_status(request.recommendation_id, request.status)
        return self.repo.get_recommendation(request.recommendation_id) or {
            "recommendation_id": request.recommendation_id,
            "status": request.status.value,
        }

    def counts(self) -> list[dict]:
        return self.repo.counts()
