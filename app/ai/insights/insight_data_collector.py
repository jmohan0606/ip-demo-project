from __future__ import annotations

from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
from app.models.opportunities import OpportunitySearchRequest
from app.models.predictions import PredictionSearchRequest
from app.models.recommendations import RecommendationSearchRequest
from app.services.context_service import ContextService
from app.services.feature_store_service import FeatureStoreService
from app.services.opportunity_service import OpportunityService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService


class InsightDataCollector:
    def __init__(self) -> None:
        self.features = FeatureStoreService()
        self.predictions = PredictionService()
        self.opportunities = OpportunityService()
        self.recommendations = RecommendationService()
        self.context = ContextService()

    def collect_for_scope(self, scope_type: str, scope_id: str, question: str | None = None) -> dict:
        entity_id = scope_id if scope_type == "Advisor" else None

        advisor_features = None
        if scope_type == "Advisor":
            advisor_features = self.features.get_vector("Advisor", scope_id, "advisor_growth_features")
            if advisor_features is None:
                self.features.materialize({"feature_groups": [], "force_refresh": True})
                advisor_features = self.features.get_vector("Advisor", scope_id, "advisor_growth_features")

        preds = self.predictions.list_predictions(PredictionSearchRequest(entity_id=entity_id, limit=20))
        opps = self.opportunities.list_opportunities(OpportunitySearchRequest(entity_id=entity_id, limit=20))
        recs = self.recommendations.list_recommendations(RecommendationSearchRequest(entity_id=entity_id, limit=20))

        context_package = None
        if scope_type in {"Advisor", "Market", "Region", "Division", "Firm"}:
            memory_scope = MemoryScopeType.ADVISOR if scope_type == "Advisor" else MemoryScopeType(scope_type)
            context_package = self.context.build_context_package(
                MemoryRetrievalRequest(scope_type=memory_scope, scope_id=scope_id, query=question, limit=10)
            )

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "advisor_features": advisor_features,
            "predictions": preds,
            "opportunities": opps,
            "recommendations": recs,
            "context_package": context_package.model_dump() if context_package else None,
        }
