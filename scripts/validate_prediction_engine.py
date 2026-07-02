from __future__ import annotations

from app.models.predictions import PredictionRunRequest, PredictionSearchRequest
from app.services.prediction_service import PredictionService


def main() -> None:
    service = PredictionService()
    result = service.run_predictions(PredictionRunRequest(write_to_tigergraph=False))
    assert result.predictions_created > 0
    rows = service.list_predictions(PredictionSearchRequest(entity_id="ADV0001", limit=20))
    assert len(rows) > 0
    counts = service.counts()
    assert len(counts) > 0
    print("Prediction Engine validation passed.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
