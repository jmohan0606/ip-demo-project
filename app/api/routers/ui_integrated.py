from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.ui_integrated_service import (
    get_dashboard_data, get_page_data, run_what_if_simulation,
    generate_recommendations, update_recommendation_feedback, ingest_document_mock,
)
from app.shared.responses import ok

router = APIRouter(prefix="/ui-integrated", tags=["Integrated UI"])

class UiContext(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"

class WhatIfRequest(UiContext):
    meeting_increase_pct: float = 10
    prospect_conversion_increase_pct: float = 8
    managed_revenue_shift_pct: float = 6
    nnm_increase_pct: float = 5
    aum_increase_pct: float = 3

class RecommendationFeedbackRequest(UiContext):
    recommendation_id: str
    action: str = Field(pattern="^(accept|reject|ignore|modify|complete)$")
    notes: str | None = None

class DocumentIngestRequest(UiContext):
    document_name: str
    document_type: str = "playbook"
    content: str = ""

@router.post("/dashboard")
def dashboard(context: UiContext):
    return ok(data=get_dashboard_data(context.model_dump()))

@router.post("/page-data/{page_id}")
def page_data(page_id: str, context: UiContext):
    return ok(data=get_page_data(page_id, context.model_dump()))

@router.post("/what-if/run")
def what_if(request: WhatIfRequest):
    return ok(data=run_what_if_simulation(request.model_dump()))

@router.post("/recommendations/generate")
def recommendations(context: UiContext):
    return ok(data=generate_recommendations(context.model_dump()))

@router.post("/recommendations/feedback")
def recommendation_feedback(request: RecommendationFeedbackRequest):
    return ok(data=update_recommendation_feedback(request.model_dump()))

@router.post("/documents/ingest")
def document_ingest(request: DocumentIngestRequest):
    return ok(data=ingest_document_mock(request.model_dump()))
