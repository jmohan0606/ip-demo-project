from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.recommendations import get_recommendation_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/recommendation-runtime", tags=["Recommendation Runtime"])


class RecommendationContext(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"


class FeedbackRequest(BaseModel):
    recommendation_id: str
    action: str = Field(pattern="^(accept|reject|ignore|modify|complete)$")
    notes: str = ""


@router.get("/status")
def status():
    return ok(data=get_recommendation_runtime().status())


@router.post("/generate")
def generate(context: RecommendationContext):
    return ok(data=get_recommendation_runtime().generate(context.model_dump()))


@router.post("/feedback")
def feedback(request: FeedbackRequest):
    return ok(data=get_recommendation_runtime().feedback(request.recommendation_id, request.action, request.notes))
