from __future__ import annotations

from app.models.predictions import PredictionRunRequest
from app.services.prediction_service import PredictionService


def main() -> None:
    result = PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
    print("Prediction run complete.")
    print(result.model_dump())


if __name__ == "__main__":
    main()
