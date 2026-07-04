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
