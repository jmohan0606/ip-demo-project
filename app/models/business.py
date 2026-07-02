from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field
from app.models.enums import FeedbackAction, RecommendationStatus
from app.models.shared import AuditFields, ExplainabilityPayload

class AdvisorProfile(BaseModel):
    advisor_id: str
    advisor_name: str
    market_id: str | None = None
    region_id: str | None = None
    division_id: str | None = None
    is_agp_enrolled: bool = False

class GoalKpiStatus(BaseModel):
    goal_id: str
    goal_name: str
    kpi_name: str
    target_value: float
    current_value: float
    expected_value: float
    attainment_percent: float
    status: str
    as_of_date: date

class PredictionResult(BaseModel):
    prediction_id: str
    entity_type: str
    entity_id: str
    prediction_type: str
    score: float
    label: str
    model_name: str
    explainability: ExplainabilityPayload | None = None
    audit: AuditFields = Field(default_factory=AuditFields)

class Opportunity(BaseModel):
    opportunity_id: str
    entity_type: str
    entity_id: str
    opportunity_type: str
    title: str
    description: str
    score: float
    explainability: ExplainabilityPayload | None = None
    audit: AuditFields = Field(default_factory=AuditFields)

class Recommendation(BaseModel):
    recommendation_id: str
    entity_type: str
    entity_id: str
    title: str
    recommendation_type: str
    action_text: str
    status: RecommendationStatus = RecommendationStatus.GENERATED
    score: float = 0.0
    explainability: ExplainabilityPayload | None = None
    audit: AuditFields = Field(default_factory=AuditFields)

class FeedbackEvent(BaseModel):
    feedback_id: str
    recommendation_id: str
    action: FeedbackAction
    reason: str | None = None
    reward_score: float | None = None
    audit: AuditFields = Field(default_factory=AuditFields)
