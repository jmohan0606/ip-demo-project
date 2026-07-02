from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.orchestration import get_orchestration_engine
from app.shared.responses import ok

router = APIRouter(prefix="/orchestration", tags=["Orchestration"])


class OrchestrationRequest(BaseModel):
    workflow: str = Field(default="dashboard")
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"
    input_payload: dict = Field(default_factory=dict)


@router.post("/run")
def run_orchestration(request: OrchestrationRequest):
    context = {
        "persona": request.persona,
        "scope_type": request.scope_type,
        "scope_id": request.scope_id,
        "period": request.period,
        "compare_to": request.compare_to,
    }
    result = get_orchestration_engine().run(
        workflow=request.workflow,
        context=context,
        input_payload=request.input_payload,
    )
    return ok(data=result)
