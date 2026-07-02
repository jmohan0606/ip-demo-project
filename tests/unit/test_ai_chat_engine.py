from app.models.ai_chat import ChatRequest
from app.services.ai_assistant_chat_service import AiAssistantChatService


def test_ai_chat_answer():
    response = AiAssistantChatService().ask(
        ChatRequest(
            question="What should I do next?",
            write_to_tigergraph=False,
            include_knowledge=False,
        )
    )
    assert response.answer
    assert response.conversation_id
