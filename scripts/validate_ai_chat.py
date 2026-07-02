from __future__ import annotations

from app.models.ai_chat import ChatPersona, ChatRequest, ChatScopeType
from app.models.predictions import PredictionRunRequest
from app.models.recommendations import RecommendationRunRequest
from app.services.ai_assistant_chat_service import AiAssistantChatService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService


def main() -> None:
    PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
    RecommendationService().run_recommendations(RecommendationRunRequest(entity_id="ADV0001", write_to_tigergraph=False, limit=50))

    service = AiAssistantChatService()
    response = service.ask(
        ChatRequest(
            question="Why is my revenue low and what should I do next?",
            persona=ChatPersona.ADVISOR,
            scope_type=ChatScopeType.ADVISOR,
            scope_id="ADV0001",
            write_to_tigergraph=False,
        )
    )
    assert response.answer
    assert response.context_items
    history = service.history(scope_id="ADV0001", limit=10)
    assert history
    print("AI Assistant Chat validation passed.")
    print(response.answer[:500])


if __name__ == "__main__":
    main()
