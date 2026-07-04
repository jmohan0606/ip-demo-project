from fastapi import APIRouter
from pydantic import BaseModel

from app.feedback.service import FeedbackLearningService
from app.shared.responses import ok

router = APIRouter(prefix="/feedback-learning", tags=["Feedback Learning"])


class FeedbackRequest(BaseModel):
    recommendation_id: str
    action: str
    action_family: str
    user_id: str = "U_ADV001"
    reason_text: str = ""
    outcome_value: float | None = None


@router.post("/submit")
def submit(request: FeedbackRequest):
    return ok(data=FeedbackLearningService().submit(
        recommendation_id=request.recommendation_id,
        action=request.action,
        action_family=request.action_family,
        user_id=request.user_id,
        reason_text=request.reason_text,
        outcome_value=request.outcome_value,
    ))


@router.get("/state")
def learning_state():
    return ok(data=FeedbackLearningService().learning_state())


@router.get("/impact-trend")
def impact_trend(advisor_ids: str = "A001,A002,A005,A015,A020,A031"):
    """Cumulative accepted/implemented/rejected trajectory + reward from replaying
    the real feedback loop over the cohort's real recommendations (no side effects)."""
    ids = [a.strip() for a in advisor_ids.split(",") if a.strip()]
    return ok(data=FeedbackLearningService().impact_trend(ids))
