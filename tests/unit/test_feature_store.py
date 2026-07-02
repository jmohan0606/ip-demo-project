from app.models.features import FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService


def test_feature_materialization_runs():
    service = FeatureStoreService()
    results = service.materialize(FeatureMaterializationRequest())
    assert len(results) >= 5
    assert any(r.records_materialized > 0 for r in results)


def test_feature_vector_lookup():
    service = FeatureStoreService()
    vector = service.get_vector("Advisor", "ADV0001", "advisor_growth_features")
    assert vector is not None
    assert "revenue_ltm" in vector["features"]
