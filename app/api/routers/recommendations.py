from fastapi import APIRouter

from app.recommendations.service import RecommendationService
from app.shared.responses import ok

router = APIRouter(prefix="/recommendations", tags=["Recommendation Engine"])


@router.post("/generate/{advisor_id}")
def generate(advisor_id: str):
    return ok(data=RecommendationService().generate_for_advisor(advisor_id))


@router.get("/advisor/{advisor_id}")
def list_for_advisor(advisor_id: str):
    """Persisted recommendations for an advisor (engine-generated + What-If-saved)."""
    return ok(data=RecommendationService().list_for_advisor(advisor_id))
