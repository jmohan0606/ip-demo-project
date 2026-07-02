from __future__ import annotations

from app.ai.chat.chat_engine import AiAssistantChatEngine
from app.ai.chat.chat_repository import ChatRepository
from app.models.ai_chat import ChatRequest, ChatResponse
from app.models.memory import ConversationTurnCreateRequest, MemoryScopeType
from app.services.memory_service import MemoryService


class AiAssistantChatService:
    def __init__(self) -> None:
        self.engine = AiAssistantChatEngine()
        self.repo = ChatRepository()
        self.memory = MemoryService()

    def ask(self, request: ChatRequest) -> ChatResponse:
        response = self.engine.answer(request)
        self.repo.save_turn(response, request.question)

        if request.write_to_memory:
            memory_scope = MemoryScopeType.ADVISOR if request.scope_type.value == "Advisor" else MemoryScopeType(request.scope_type.value)
            self.memory.save_conversation_turn(
                ConversationTurnCreateRequest(
                    conversation_id=response.conversation_id,
                    user_question=request.question,
                    assistant_answer=response.answer,
                    persona=request.persona.value,
                    scope_type=memory_scope,
                    scope_id=request.scope_id,
                ),
                write_to_graph=request.write_to_tigergraph,
            )

        return response

    def history(self, conversation_id: str | None = None, scope_id: str | None = None, limit: int = 50) -> list[dict]:
        return self.repo.history(conversation_id, scope_id, limit)
