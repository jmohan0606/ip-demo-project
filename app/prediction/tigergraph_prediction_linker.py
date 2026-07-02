from __future__ import annotations

from app.ingestion.tigergraph_upsert import TigerGraphUpsertClient
from app.models.predictions import PredictionRecord


class TigerGraphPredictionLinker:
    def __init__(self) -> None:
        self.upsert = TigerGraphUpsertClient()

    def upsert_prediction(self, prediction: PredictionRecord) -> dict:
        payload = {
            "prediction_id": prediction.prediction_id,
            "prediction_type": prediction.prediction_type.value,
            "score": prediction.score,
            "label": prediction.label,
            "model_name": prediction.model_name,
            "model_version": prediction.model_version,
            "generated_ts": prediction.generated_ts.isoformat(),
            "confidence": prediction.confidence,
            "status": prediction.status,
        }
        result = self.upsert.upsert_vertex("phx_dm_prediction_result", prediction.prediction_id, payload)
        self.upsert.upsert_edge("phx_dm_prediction_for_advisor", prediction.prediction_id, prediction.entity_id, {})
        return result
