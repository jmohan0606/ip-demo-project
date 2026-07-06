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


@router.get("/context-trace")
def context_trace(question: str, scope_type: str = "Advisor", scope_id: str = "A001"):
    """Section 11.6 — the visible context-engineering pipeline: resolved scope -> retrieved
    context items (with rerank scores) -> pruning -> what reaches the prompt."""
    from app.ai.chat.context_assembler import ChatContextAssembler
    from app.models.ai_chat import ChatRequest, ChatScopeType
    req = ChatRequest(question=question, scope_type=ChatScopeType(scope_type), scope_id=scope_id)
    _, trace = ChatContextAssembler().assemble_with_trace(req)
    return ok(data=trace)
