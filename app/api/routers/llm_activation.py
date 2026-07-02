from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.ai_assistant_runtime import get_ai_assistant_runtime
from app.llm import get_llm_runtime
from app.shared.responses import ok

router = APIRouter(prefix="/llm-activation", tags=["LLM Activation"])


class AssistantAskRequest(BaseModel):
    persona: str = "Advisor"
    scope_type: str = "Advisor"
    scope_id: str = "ADV0001"
    period: str = "YTD"
    compare_to: str = "Prior Year"
    question: str = "Why did revenue decline and what should I do next?"


@router.get("/status")
def status():
    return ok(data={
        "llm_runtime": get_llm_runtime().status(),
        "assistant_runtime": get_ai_assistant_runtime().status(),
    })


@router.post("/ask")
def ask(request: AssistantAskRequest):
    context = {
        "persona": request.persona,
        "scope_type": request.scope_type,
        "scope_id": request.scope_id,
        "period": request.period,
        "compare_to": request.compare_to,
    }
    return ok(data=get_ai_assistant_runtime().ask(context, request.question))


@router.post("/recommendation-narrative")
def recommendation_narrative(request: AssistantAskRequest):
    context = {
        "persona": request.persona,
        "scope_type": request.scope_type,
        "scope_id": request.scope_id,
        "period": request.period,
        "compare_to": request.compare_to,
    }
    return ok(data=get_ai_assistant_runtime().recommendation_narrative(context))
