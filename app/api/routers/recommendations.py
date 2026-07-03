from fastapi import APIRouter

from app.recommendations.service import RecommendationService
from app.shared.responses import ok

router = APIRouter(prefix="/recommendations", tags=["Recommendation Engine"])


@router.post("/generate/{advisor_id}")
def generate(advisor_id: str):
    return ok(data=RecommendationService().generate_for_advisor(advisor_id))
