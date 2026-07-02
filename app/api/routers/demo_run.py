from __future__ import annotations

from fastapi import APIRouter

from app.services.demo_orchestration_service import DemoOrchestrationService
from app.shared.responses import ok

router = APIRouter(prefix="/demo-run", tags=["End-to-End Demo Run"])


@router.post("/full")
def run_full_demo(advisor_id: str = "ADV0001"):
    return ok(data=DemoOrchestrationService().run_full_demo(advisor_id).model_dump())
