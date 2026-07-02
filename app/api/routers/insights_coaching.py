from __future__ import annotations

from fastapi import APIRouter

from app.models.insights_coaching import InsightRequest
from app.services.insights_coaching_service import InsightsCoachingService
from app.shared.responses import ok

router = APIRouter(prefix="/insights-coaching", tags=["AI Insights & Coaching"])


@router.post("/generate")
def generate(request: InsightRequest):
    return ok(data=InsightsCoachingService().generate_dashboard_payload(request).model_dump())


@router.get("/cards")
def cards(scope_id: str | None = None, limit: int = 100):
    return ok(data=InsightsCoachingService().list_cards(scope_id, limit))


@router.get("/counts")
def counts():
    return ok(data=InsightsCoachingService().counts())
