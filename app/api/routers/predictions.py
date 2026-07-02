from __future__ import annotations

from fastapi import APIRouter

from app.models.predictions import PredictionRunRequest, PredictionSearchRequest
from app.services.prediction_service import PredictionService
from app.shared.responses import ok

router = APIRouter(prefix="/predictions", tags=["Prediction Engine"])


@router.post("/run")
def run_predictions(request: PredictionRunRequest):
    return ok(data=PredictionService().run_predictions(request).model_dump())


@router.post("/search")
def search_predictions(request: PredictionSearchRequest):
    return ok(data=PredictionService().list_predictions(request))


@router.get("/counts")
def counts():
    return ok(data=PredictionService().counts())


@router.get("/models")
def models():
    return ok(data=PredictionService().model_metadata())
