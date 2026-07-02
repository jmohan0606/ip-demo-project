from __future__ import annotations

from fastapi import APIRouter

from app.models.feedback_learning import FeedbackSearchRequest, FeedbackSubmitRequest
from app.services.feedback_learning_service import FeedbackLearningService
from app.shared.responses import ok

router = APIRouter(prefix="/feedback-learning", tags=["Feedback Learning"])


@router.post("/submit")
def submit_feedback(request: FeedbackSubmitRequest):
    return ok(data=FeedbackLearningService().submit_feedback(request).model_dump())


@router.post("/search")
def search_feedback(request: FeedbackSearchRequest):
    return ok(data=FeedbackLearningService().list_feedback(request))


@router.get("/learning-signals")
def learning_signals(limit: int = 100):
    return ok(data=FeedbackLearningService().list_learning_signals(limit))


@router.get("/counts")
def counts():
    return ok(data=FeedbackLearningService().counts())
