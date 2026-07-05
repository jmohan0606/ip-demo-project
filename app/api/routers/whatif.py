from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.shared.responses import ok
from app.whatif.service import WhatIfService

router = APIRouter(prefix="/whatif", tags=["What-If Simulator"])


class WhatIfRequest(BaseModel):
    advisor_id: str = "A001"
    meeting_increase_pct: float = 0.0
    prospecting_increase_pct: float = 0.0
    aum_growth_pct: float = 0.0
    goal_reviews_added: float = 0.0
    horizon_months: int = 6


@router.post("/simulate")
def simulate(request: WhatIfRequest):
    return ok(data=WhatIfService().simulate(
        advisor_id=request.advisor_id,
        meeting_increase_pct=request.meeting_increase_pct,
        prospecting_increase_pct=request.prospecting_increase_pct,
        aum_growth_pct=request.aum_growth_pct,
        goal_reviews_added=request.goal_reviews_added,
        horizon_months=request.horizon_months,
    ))


class SaveScenarioRequest(BaseModel):
    advisor_id: str
    title: str
    category: str = "GROWTH"
    high_priority: bool = False
    levers: dict = {}
    metrics: list[dict] = []
    snapshot_id: str | None = None
    created_date: str | None = None


@router.post("/save-recommendation")
def save_recommendation(request: SaveScenarioRequest):
    """Save a What-If scenario result as a REAL recommendation through the
    recommendations pipeline (CLAUDE.md 9.5) — retrievable everywhere recs are."""
    from app.recommendations.service import RecommendationService

    return ok(data=RecommendationService().save_scenario_as_recommendation(
        advisor_id=request.advisor_id, title=request.title, category=request.category,
        levers=request.levers, metrics=request.metrics, snapshot_id=request.snapshot_id,
        high_priority=request.high_priority, created_date=request.created_date,
    ))
