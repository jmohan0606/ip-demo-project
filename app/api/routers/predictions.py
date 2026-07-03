from fastapi import APIRouter

from app.prediction.service import PredictionService
from app.shared.responses import ok

router = APIRouter(prefix="/predictions", tags=["Prediction Engine"])


@router.post("/run/{advisor_id}")
def run_predictions(advisor_id: str):
    return ok(data=PredictionService().predict_advisor(advisor_id))


@router.get("/revenue-decline/{advisor_id}")
def revenue_decline(advisor_id: str):
    return ok(data=PredictionService().predict_revenue_decline(advisor_id, persist=False))


@router.get("/agp-off-track/{advisor_id}")
def agp_off_track(advisor_id: str):
    return ok(data=PredictionService().predict_agp_off_track(advisor_id, persist=False))
