from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.features import get_feature_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/feature-runtime", tags=["Feature Runtime"])


class FeatureContext(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"


class PredictionRequest(FeatureContext):
    scenario: dict = Field(default_factory=dict)


@router.get("/status")
def status():
    return ok(data=get_feature_runtime().status())


@router.post("/features")
def features(context: FeatureContext):
    return ok(data=get_feature_runtime().get_feature_summary(context.model_dump()))


@router.post("/similarity")
def similarity(context: FeatureContext):
    return ok(data=get_feature_runtime().similarity_search(context.model_dump()))


@router.post("/predict")
def predict(request: PredictionRequest):
    return ok(data=get_feature_runtime().predict(request.model_dump(), request.scenario))
