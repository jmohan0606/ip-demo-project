from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class PredictionType(StrEnum):
    REVENUE_GROWTH = "Revenue Growth"
    NNM_GROWTH = "NNM Growth"
    AUM_GROWTH = "AUM Growth"
    AGP_GOAL_RISK = "AGP Goal Risk"
    ADVISOR_SUCCESS = "Advisor Success Score"
    OPPORTUNITY_PROPENSITY = "Opportunity Propensity"


class PredictionLabel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    AT_RISK = "At Risk"
    ON_TRACK = "On Track"


class PredictionRunRequest(BaseModel):
    prediction_types: list[PredictionType] = Field(default_factory=list)
    write_to_tigergraph: bool = True
    force_refresh_features: bool = False


class PredictionRecord(BaseModel):
    prediction_id: str
    entity_type: str = "Advisor"
    entity_id: str
    prediction_type: PredictionType
    score: float
    label: str
    model_name: str = "sklearn_local_demo_model"
    model_version: str = "1.0"
    confidence: float = 0.80
    explanation: str
    feature_snapshot: dict = Field(default_factory=dict)
    generated_ts: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class PredictionRunResult(BaseModel):
    predictions_created: int
    model_name: str
    status: str
    message: str


class PredictionSearchRequest(BaseModel):
    entity_id: str | None = None
    prediction_type: PredictionType | None = None
    limit: int = 100
