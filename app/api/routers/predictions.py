from fastapi import APIRouter

from app.ml.client import get_model_client
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


@router.get("/household-churn/{advisor_id}")
def household_churn(advisor_id: str):
    """Per-household severe-attrition propensity (Section 11.1 §3.5). Indicative until the
    model passes its serving gate; the response carries the honest gate status + caveat."""
    return ok(data=get_model_client().household_churn(advisor_id))
