from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.recommendations.service import RecommendationService
from app.recommendations.lifecycle import RecommendationLifecycleService, LifecycleError
from app.feedback.service import FeedbackLearningService
from app.shared.responses import ok

router = APIRouter(prefix="/recommendations", tags=["Recommendation Engine"])


@router.post("/generate/{advisor_id}")
def generate(advisor_id: str):
    return ok(data=RecommendationService().generate_for_advisor(advisor_id))


@router.get("/advisor/{advisor_id}")
def list_for_advisor(advisor_id: str):
    """Persisted recommendations for an advisor (engine-generated + What-If-saved)."""
    return ok(data=RecommendationService().list_for_advisor(advisor_id))


class TransitionRequest(BaseModel):
    action: str  # accept | start | complete | modify | reject | ignore | reopen
    actor_type: str = "advisor"
    actor_id: str | None = None
    note: str | None = None


# Actions that carry a learning signal go through the feedback service (so the bandit
# weight always moves in step with status); start/reopen are pure lifecycle moves.
_FEEDBACK_ACTIONS = {"accept", "complete", "modify", "reject", "ignore"}


@router.post("/{recommendation_id}/transition")
def transition(recommendation_id: str, request: TransitionRequest):
    """Section 13.1 — drive the recommendation state machine. `accept/complete/modify/
    reject/ignore` delegate to the feedback service (status + learning signal together);
    `start/reopen` are pure lifecycle moves. 409 on an illegal/terminal transition."""
    action = request.action.lower()
    try:
        if action in _FEEDBACK_ACTIONS:
            lc = RecommendationLifecycleService()
            attrs = lc._rec_attrs(recommendation_id)
            result = FeedbackLearningService().submit(
                recommendation_id=recommendation_id, action=action,
                action_family=attrs.get("action_family") or "CRM_EXECUTION",
                user_id=request.actor_id or "U_ADV001", reason_text=request.note or "")
            return ok(data=result["lifecycle"])
        return ok(data=RecommendationLifecycleService().apply_action(
            recommendation_id, action, actor_type=request.actor_type,
            actor_id=request.actor_id, note=request.note))
    except LifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{recommendation_id}/lifecycle")
def lifecycle(recommendation_id: str):
    """Full lifecycle audit for the explainability panel + ledger row expansion."""
    return ok(data=RecommendationLifecycleService().lifecycle_for(recommendation_id))
