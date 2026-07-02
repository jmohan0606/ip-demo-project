from __future__ import annotations

from uuid import uuid4

from app.config import get_runtime_config
from app.features.feature_engineering import FeatureEngineeringService
from app.features.models import FeatureVector
from app.features.prediction_runtime import PredictionRuntime
from app.features.similarity import SimilarityService
from app.features.sqlite_feature_store import SQLiteFeatureStore
from app.graph import get_graph_runtime


class FeatureRuntime:
    def __init__(self) -> None:
        self.config = get_runtime_config()
        self.store = SQLiteFeatureStore(self.config.sqlite_db_path)
        self.engineering = FeatureEngineeringService()
        self.prediction = PredictionRuntime()
        self.similarity = SimilarityService()
        self.graph = get_graph_runtime()
        self._seed_demo_vectors()

    def _seed_demo_vectors(self) -> None:
        demo = [
            FeatureVector("Advisor", "ADV0002", {"revenue_ytd": 4_550_000, "revenue_growth_pct": 10.2, "managed_revenue_pct": 43, "household_count": 250, "aum": 88_000_000, "nnm": 6_900_000, "ncf": 1_600_000, "meeting_cadence": 3.1, "crm_followups_open": 13, "agp_goal_attainment_pct": 70, "recommendation_accept_rate_pct": 61, "peer_gap_pct": -4.9}, {"name": "Maya Chen"}),
            FeatureVector("Advisor", "ADV0003", {"revenue_ytd": 4_910_000, "revenue_growth_pct": 13.5, "managed_revenue_pct": 47, "household_count": 280, "aum": 101_000_000, "nnm": 7_600_000, "ncf": 2_100_000, "meeting_cadence": 3.7, "crm_followups_open": 9, "agp_goal_attainment_pct": 77, "recommendation_accept_rate_pct": 66, "peer_gap_pct": -3.1}, {"name": "Noah Williams"}),
            FeatureVector("Advisor", "ADV0004", {"revenue_ytd": 2_900_000, "revenue_growth_pct": -3.2, "managed_revenue_pct": 31, "household_count": 190, "aum": 61_000_000, "nnm": -420_000, "ncf": -180_000, "meeting_cadence": 1.8, "crm_followups_open": 22, "agp_goal_attainment_pct": 48, "recommendation_accept_rate_pct": 33, "peer_gap_pct": -14.0}, {"name": "Risk Watch Advisor"}),
        ]
        for vector in demo:
            self.store.upsert_feature_vector(vector)

    def status(self) -> dict:
        counts = self.store.count()
        return {
            "feature_store_backend": "sqlite",
            "sqlite_db_path": self.config.sqlite_db_path,
            "feature_vectors": counts["feature_vectors"],
            "prediction_results": counts["prediction_results"],
            "graph_embedding_backend": self.config.graph_embedding_backend,
        }

    def get_or_create_advisor_vector(self, context: dict) -> FeatureVector:
        entity_id = context.get("scope_id", "ADV0001")
        vector = self.store.get_feature_vector("Advisor", entity_id)
        if vector:
            return vector
        vector = self.engineering.build_advisor_features(context)
        self.store.upsert_feature_vector(vector)
        self.graph.upsert_vertex("FeatureVector", f"FV-{vector.entity_type}-{vector.entity_id}", {
            "entity_type": vector.entity_type,
            "entity_id": vector.entity_id,
            "feature_count": len(vector.features),
        })
        return vector

    def get_feature_summary(self, context: dict) -> dict:
        vector = self.get_or_create_advisor_vector(context)
        return {
            "entity_type": vector.entity_type,
            "entity_id": vector.entity_id,
            "features": vector.features,
            "metadata": vector.metadata,
            "status": self.status(),
        }

    def similarity_search(self, context: dict, top_k: int = 5) -> dict:
        target = self.get_or_create_advisor_vector(context)
        candidates = self.store.list_feature_vectors("Advisor")
        results = self.similarity.top_similar(target, candidates, top_k)
        return {
            "target": {"entity_type": target.entity_type, "entity_id": target.entity_id},
            "results": [result.__dict__ for result in results],
        }

    def predict(self, context: dict, scenario: dict | None = None) -> dict:
        vector = self.get_or_create_advisor_vector(context)
        scenario = scenario or {}
        results = [
            self.prediction.forecast_revenue(vector, scenario),
            self.prediction.forecast_nnm(vector, scenario),
            self.prediction.forecast_agp_goal(vector, scenario),
        ]
        serialized = [result.__dict__ for result in results]
        for result in serialized:
            prediction_id = f"PRED-{uuid4().hex[:10].upper()}"
            self.store.save_prediction(prediction_id, vector.entity_type, vector.entity_id, result["target"], result)
            self.graph.upsert_vertex("Prediction", prediction_id, {
                "prediction_id": prediction_id,
                "entity_type": vector.entity_type,
                "entity_id": vector.entity_id,
                "target": result["target"],
                "baseline": result["baseline"],
                "predicted": result["predicted"],
                "confidence": result["confidence"],
            })
        return {
            "entity": {"entity_type": vector.entity_type, "entity_id": vector.entity_id},
            "scenario": scenario,
            "predictions": serialized,
        }


_feature_runtime: FeatureRuntime | None = None


def get_feature_runtime() -> FeatureRuntime:
    global _feature_runtime
    if _feature_runtime is None:
        _feature_runtime = FeatureRuntime()
    return _feature_runtime
