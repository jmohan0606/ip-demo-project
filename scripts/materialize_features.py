from __future__ import annotations

from app.models.features import FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService


def main() -> None:
    results = FeatureStoreService().materialize(FeatureMaterializationRequest())
    print("Feature materialization completed.")
    for result in results:
        print(f"- {result.feature_group}: {result.records_materialized}")


if __name__ == "__main__":
    main()
