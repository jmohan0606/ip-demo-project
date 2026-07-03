from fastapi import APIRouter

from app.opportunities.service import OpportunityDetectionService
from app.shared.responses import ok

router = APIRouter(prefix="/opportunities", tags=["Opportunity Engine"])


@router.post("/detect/{advisor_id}")
def detect(advisor_id: str):
    return ok(data=OpportunityDetectionService().detect_for_advisor(advisor_id))
