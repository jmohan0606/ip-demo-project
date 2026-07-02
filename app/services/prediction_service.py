from __future__ import annotations

from app.models.predictions import PredictionRunRequest, PredictionRunResult, PredictionSearchRequest, PredictionType
from app.prediction.feature_matrix_builder import FeatureMatrixBuilder
from app.prediction.prediction_engine import LocalPredictionEngine
from app.prediction.prediction_repository import PredictionRepository
from app.prediction.tigergraph_prediction_linker import TigerGraphPredictionLinker


class PredictionService:
    def __init__(self) -> None:
        self.matrix_builder = FeatureMatrixBuilder()
        self.engine = LocalPredictionEngine()
        self.repo = PredictionRepository()
        self.linker = TigerGraphPredictionLinker()

    def run_predictions(self, request: PredictionRunRequest) -> PredictionRunResult:
        prediction_types = request.prediction_types or [
            PredictionType.REVENUE_GROWTH,
            PredictionType.NNM_GROWTH,
            PredictionType.AUM_GROWTH,
            PredictionType.AGP_GOAL_RISK,
            PredictionType.ADVISOR_SUCCESS,
            PredictionType.OPPORTUNITY_PROPENSITY,
        ]
        df = self.matrix_builder.advisor_matrix()
        total = 0
        for ptype in prediction_types:
            records, metadata = self.engine.predict(df, ptype)
            self.repo.save_model_metadata(f"{ptype.value}_v1", metadata)
            for record in records:
                self.repo.save_prediction(record)
                if request.write_to_tigergraph:
                    self.linker.upsert_prediction(record)
            total += len(records)

        return PredictionRunResult(
            predictions_created=total,
            model_name=self.engine.model_name,
            status="completed",
            message=f"Generated {total} predictions across {len(prediction_types)} prediction types.",
        )

    def list_predictions(self, request: PredictionSearchRequest) -> list[dict]:
        return self.repo.list_predictions(
            entity_id=request.entity_id,
            prediction_type=request.prediction_type.value if request.prediction_type else None,
            limit=request.limit,
        )

    def counts(self) -> list[dict]:
        return self.repo.counts()

    def model_metadata(self) -> list[dict]:
        return self.repo.model_metadata()
