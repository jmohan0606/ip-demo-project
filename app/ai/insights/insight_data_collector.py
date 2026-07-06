from __future__ import annotations

from app.features.engineering import FeatureEngineeringService
from app.models.memory import MemoryRetrievalRequest, MemoryScopeType
from app.opportunities.service import OpportunityDetectionService
from app.prediction.service import PredictionService as PipelinePredictionService
from app.recommendations.service import RecommendationService as PipelineRecommendationService
from app.services.context_service import ContextService


class InsightDataCollector:
    """Collects grounding data from the Phase-5..9 pipeline (the same feature/
    prediction/opportunity/recommendation services the agents read) — replaces the
    old FeatureStoreService family, whose vectors returned zeros for current data."""

    def __init__(self) -> None:
        self.context = ContextService()

    def collect_for_scope(self, scope_type: str, scope_id: str, question: str | None = None) -> dict:
        advisor_features = None
        preds: list[dict] = []
        opps: list[dict] = []
        recs: list[dict] = []

        if scope_type == "Advisor":
            snapshot = FeatureEngineeringService().compute_advisor_snapshot(scope_id)
            advisor_features = {
                "entity_type": "Advisor",
                "entity_id": scope_id,
                "feature_snapshot_id": snapshot.snapshot_id,
                "feature_version": snapshot.feature_version,
                "features": snapshot.values(),
                "lineage": snapshot.lineage(),
            }
            preds = [
                p for p in PipelinePredictionService().predict_advisor(scope_id)["predictions"]
                if p.get("score") is not None
            ]
            opps = OpportunityDetectionService().detect_for_advisor(scope_id)["opportunities"]
            recs = PipelineRecommendationService().generate_for_advisor(scope_id)["recommendations"]

        context_package = None
        if scope_type in {"Advisor", "Market", "Region", "Division", "Firm"}:
            memory_scope = MemoryScopeType.ADVISOR if scope_type == "Advisor" else MemoryScopeType(scope_type)
            context_package = self.context.build_context_package(
                MemoryRetrievalRequest(scope_type=memory_scope, scope_id=scope_id, query=question, limit=10)
            )

        # Section 13.4: completed-recommendation lifecycle + recorded impact for Advisor scope.
        lifecycle = None
        if scope_type == "Advisor":
            try:
                from app.recommendations.lifecycle import RecommendationLifecycleService
                lifecycle = RecommendationLifecycleService().recent_activity_for_advisor(scope_id, limit=5)
            except Exception:
                lifecycle = None

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "advisor_features": advisor_features,
            "predictions": preds,
            "opportunities": opps,
            "recommendations": recs,
            "context_package": context_package.model_dump() if context_package else None,
            "lifecycle": lifecycle,
        }
