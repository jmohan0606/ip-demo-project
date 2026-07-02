from __future__ import annotations

from fastapi import APIRouter

from app.models.ai_chat import ChatRequest
from app.services.ai_assistant_chat_service import AiAssistantChatService
from app.shared.responses import ok

router = APIRouter(prefix="/ai-chat", tags=["AI Assistant Chat"])


@router.post("/ask")
def ask(request: ChatRequest):
    return ok(data=AiAssistantChatService().ask(request).model_dump())


@router.get("/history")
def history(conversation_id: str | None = None, scope_id: str | None = None, limit: int = 50):
    return ok(data=AiAssistantChatService().history(conversation_id, scope_id, limit))
