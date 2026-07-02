from __future__ import annotations

from app.models.features import FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService


def main() -> None:
    service = FeatureStoreService()
    results = service.materialize(FeatureMaterializationRequest())
    assert len(results) >= 5
    counts = service.counts()
    assert len(counts) >= 5
    advisor = service.get_vector("Advisor", "ADV0001", "advisor_growth_features")
    assert advisor is not None
    print("Feature Store validation passed.")
    for row in counts:
        print(row)


if __name__ == "__main__":
    main()
