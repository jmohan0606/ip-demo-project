from __future__ import annotations

from app.models.opportunities import OpportunityRunRequest
from app.models.recommendations import RecommendationActionRequest, RecommendationRunRequest, RecommendationRunResult, RecommendationSearchRequest
from app.recommendations.recommendation_engine import RecommendationEngine
from app.recommendations.recommendation_repository import RecommendationRepository
from app.recommendations.tigergraph_recommendation_linker import TigerGraphRecommendationLinker
from app.services.opportunity_service import OpportunityService


class RecommendationService:
    def __init__(self) -> None:
        self.opportunity_service = OpportunityService()
        self.engine = RecommendationEngine()
        self.repo = RecommendationRepository()
        self.linker = TigerGraphRecommendationLinker()

    def run_recommendations(self, request: RecommendationRunRequest) -> RecommendationRunResult:
        # Ensure opportunities exist.
        self.opportunity_service.run_opportunities(
            OpportunityRunRequest(
                entity_id=request.entity_id,
                write_to_tigergraph=False,
                min_score=request.min_opportunity_score,
                limit=request.limit,
            )
        )
        recommendations = self.engine.generate(request.entity_id, request.min_opportunity_score, request.limit)
        for rec in recommendations:
            self.repo.save_recommendation(rec)
            if request.write_to_tigergraph:
                self.linker.upsert_recommendation(rec)

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
