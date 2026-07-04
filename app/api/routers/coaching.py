from __future__ import annotations

from fastapi import APIRouter

from app.coaching.service import CoachingReviewService
from app.shared.responses import ok

router = APIRouter(prefix="/coaching", tags=["Coaching & Reviews"])


@router.get("/advisor/{advisor_id}")
def advisor(advisor_id: str):
    """Coaching sessions + manager reviews for an advisor from the graph."""
    return ok(data=CoachingReviewService().advisor(advisor_id))
