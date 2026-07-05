from __future__ import annotations

import pandas as pd
from app.feature_store.feature_store_repository import FeatureStoreRepository
from app.models.features import FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService


class FeatureMatrixBuilder:
    def __init__(self) -> None:
        self.feature_service = FeatureStoreService()
        self.repo = FeatureStoreRepository()

    def ensure_features(self) -> None:
        self.feature_service.materialize(FeatureMaterializationRequest())

    def advisor_matrix(self) -> pd.DataFrame:
        self.ensure_features()
        growth = self.repo.list_vectors("advisor_growth_features", limit=10000)
        crm = self.repo.list_vectors("crm_activity_features", limit=10000)
        agp = self.repo.list_vectors("agp_progress_features", limit=10000)

        rows: dict[str, dict] = {}
        for item in growth + crm + agp:
            entity_id = item["entity_id"]
            rows.setdefault(entity_id, {"entity_id": entity_id})
            for k, v in item["features"].items():
                if isinstance(v, bool):
                    rows[entity_id][k] = int(v)
                elif isinstance(v, (int, float)):
                    rows[entity_id][k] = v
                elif isinstance(v, str):
                    # keep strings out of sklearn matrix for now
                    continue

        df = pd.DataFrame(list(rows.values())).fillna(0)
        return df
