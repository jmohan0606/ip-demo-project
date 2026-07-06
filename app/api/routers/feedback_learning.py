from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.feedback.service import FeedbackLearningService
from app.recommendations.lifecycle import LifecycleError
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
    try:
        return ok(data=FeedbackLearningService().submit(
            recommendation_id=request.recommendation_id,
            action=request.action,
            action_family=request.action_family,
            user_id=request.user_id,
            reason_text=request.reason_text,
            outcome_value=request.outcome_value,
        ))
    except LifecycleError as exc:
        # Section 13.1: a feedback action on a terminal recommendation is rejected.
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/state")
def learning_state():
    return ok(data=FeedbackLearningService().learning_state())


@router.get("/impact-trend")
def impact_trend(advisor_ids: str = "A001,A002,A005,A015,A020,A031"):
    """Cumulative accepted/implemented/rejected trajectory + reward from replaying
    the real feedback loop over the cohort's real recommendations (no side effects)."""
    ids = [a.strip() for a in advisor_ids.split(",") if a.strip()]
    return ok(data=FeedbackLearningService().impact_trend(ids))


class RetrainRequest(BaseModel):
    dry_run: bool = False


@router.post("/retrain")
def retrain(request: RetrainRequest):
    """Section 11.3 — outcome-driven learning: fine-tune the GNN on the real recorded
    outcome history (successful vs unsuccessful) and return before/after metrics. dry_run
    previews pairs + baseline metrics without writing the -ft model."""
    from app.ml.fl_finetune import run_finetune

    return ok(data=run_finetune(dry_run=request.dry_run))


@router.get("/before-after")
def before_after(advisor_id: str = "A001", top_k: int = 5):
    """The before/after demonstration payload — similar advisors + per-family outcome
    affinity under the base vs the outcome-fine-tuned embeddings."""
    from app.ml.fl_service import before_after as _ba

    return ok(data=_ba(advisor_id, top_k))


@router.get("/outcome-learning")
def outcome_learning():
    """Status of the deeper (outcome-driven) learning layer."""
    from app.ml.fl_service import outcome_learning_state

    return ok(data=outcome_learning_state())
