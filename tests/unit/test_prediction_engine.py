from app.models.predictions import PredictionRunRequest
from app.services.prediction_service import PredictionService


def test_prediction_run():
    result = PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
    assert result.predictions_created > 0
