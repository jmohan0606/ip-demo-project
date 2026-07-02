from __future__ import annotations

from app.feature_store.feature_engineering import FeatureEngineeringPipeline
from app.feature_store.feature_registry import list_feature_definitions
from app.feature_store.feature_store_repository import FeatureStoreRepository
from app.models.features import FeatureGroupName, FeatureMaterializationRequest, FeatureMaterializationResult


class FeatureStoreService:
    def __init__(self) -> None:
        self.repo = FeatureStoreRepository()
        self.pipeline = FeatureEngineeringPipeline()

    def register_features(self) -> int:
        definitions = list_feature_definitions()
        for definition in definitions:
            self.repo.save_definition(definition)
        return len(definitions)

    def materialize(self, request: FeatureMaterializationRequest) -> list[FeatureMaterializationResult]:
        self.register_features()
        groups = request.feature_groups or [
            FeatureGroupName.ADVISOR_GROWTH,
            FeatureGroupName.CRM_ACTIVITY,
            FeatureGroupName.AGP_PROGRESS,
            FeatureGroupName.HOUSEHOLD_OPPORTUNITY,
            FeatureGroupName.ACCOUNT_REVENUE,
        ]

        results = []
        for group in groups:
            if group == FeatureGroupName.ADVISOR_GROWTH:
                vectors = self.pipeline.advisor_growth_features()
            elif group == FeatureGroupName.CRM_ACTIVITY:
                vectors = self.pipeline.crm_activity_features()
            elif group == FeatureGroupName.AGP_PROGRESS:
                vectors = self.pipeline.agp_progress_features()
            elif group == FeatureGroupName.HOUSEHOLD_OPPORTUNITY:
                vectors = self.pipeline.household_opportunity_features()
            elif group == FeatureGroupName.ACCOUNT_REVENUE:
                vectors = self.pipeline.account_revenue_features()
            else:
                vectors = []

            for vector in vectors:
                self.repo.save_feature_vector(vector)

            entity_type = vectors[0].entity_type if vectors else "Unknown"
            results.append(FeatureMaterializationResult(
                feature_group=group,
                entity_type=entity_type,
                records_materialized=len(vectors),
                status="completed",
                message=f"Materialized {len(vectors)} vectors for {group.value}",
            ))
        return results

    def list_vectors(self, feature_group: str | None = None, limit: int = 100) -> list[dict]:
        return self.repo.list_vectors(feature_group, limit)

    def get_vector(self, entity_type: str, entity_id: str, feature_group: str) -> dict | None:
        return self.repo.get_feature_vector(entity_type, entity_id, feature_group)

    def counts(self) -> list[dict]:
        return self.repo.feature_counts()
