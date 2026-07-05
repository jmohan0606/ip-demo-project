from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.coaching.service import CoachingReviewService
from app.shared.responses import ok

router = APIRouter(prefix="/coaching", tags=["Coaching & Reviews"])


@router.get("/advisor/{advisor_id}")
def advisor(advisor_id: str):
    """Coaching sessions + manager reviews for an advisor from the graph."""
    return ok(data=CoachingReviewService().advisor(advisor_id))


@router.get("/task-catalog")
def task_catalog():
    """Selectable coaching-task templates a manager can assign."""
    return ok(data={"catalog": CoachingReviewService().task_catalog()})


@router.get("/tasks/{advisor_id}")
def tasks(advisor_id: str):
    """Manager-assigned coaching tasks for an advisor, with status."""
    return ok(data=CoachingReviewService().tasks(advisor_id))


class CreateTaskRequest(BaseModel):
    advisor_id: str
    title: str
    category: str
    instruction: str
    priority: str = "MEDIUM"
    due_date: str | None = None
    created_by_user_id: str = "U_MDW01"
    created_date: str | None = None


@router.post("/tasks")
def create_task(request: CreateTaskRequest):
    """Manager assigns a coaching task — persisted to the graph, retrievable later."""
    return ok(data=CoachingReviewService().create_task(
        advisor_id=request.advisor_id, title=request.title, category=request.category,
        instruction=request.instruction, priority=request.priority, due_date=request.due_date,
        created_by_user_id=request.created_by_user_id, created_date=request.created_date,
    ))


class UpdateTaskStatusRequest(BaseModel):
    status: str
    completed_date: str | None = None


@router.patch("/tasks/{task_id}/status")
def update_task_status(task_id: str, request: UpdateTaskStatusRequest):
    return ok(data=CoachingReviewService().update_task_status(task_id, request.status, request.completed_date))
