from __future__ import annotations

import streamlit as st

from app.models.ai_chat import ChatPersona, ChatRequest, ChatScopeType
from app.models.predictions import PredictionRunRequest
from app.models.recommendations import RecommendationRunRequest
from app.services.ai_assistant_chat_service import AiAssistantChatService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService


def render_ai_assistant_chat_page() -> None:
    st.title("AI Assistant Chat")
    st.caption("Ask questions using context memory, knowledge/RAG, predictions, opportunities, recommendations and insights.")

    chat_service = AiAssistantChatService()

    with st.sidebar:
        st.subheader("Chat Context")
        persona = st.selectbox("Persona", [p.value for p in ChatPersona])
        scope_type = st.selectbox("Scope Type", [s.value for s in ChatScopeType], index=4)
        scope_id = st.text_input("Scope ID", value="ADV0001")
        include_memory = st.checkbox("Use Context Memory", value=True)
        include_knowledge = st.checkbox("Use Knowledge RAG", value=True)
        include_insights = st.checkbox("Use Insights", value=True)
        write_memory = st.checkbox("Save Conversation Memory", value=True)
        write_tg = st.checkbox("Write to TigerGraph", value=False)

        if st.button("Prepare Demo Signals"):
            PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
            RecommendationService().run_recommendations(RecommendationRunRequest(entity_id=scope_id if scope_type == "Advisor" else None, write_to_tigergraph=False, limit=100))
            st.success("Predictions, opportunities and recommendations prepared.")

    if "iperform_chat_history" not in st.session_state:
        st.session_state.iperform_chat_history = []

    for msg in st.session_state.iperform_chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Ask about performance, opportunities, recommendations, AGP coaching, or next best actions...")
    if question:
        st.session_state.iperform_chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.status("Retrieving context and generating answer...", expanded=False):
                response = chat_service.ask(
                    ChatRequest(
                        question=question,
                        persona=ChatPersona(persona),
                        scope_type=ChatScopeType(scope_type),
                        scope_id=scope_id,
                        include_memory=include_memory,
                        include_knowledge=include_knowledge,
                        include_insights=include_insights,
                        write_to_memory=write_memory,
                        write_to_tigergraph=write_tg,
                    )
                )
            st.write(response.answer)
            with st.expander("Context Used"):
                st.json([c.model_dump() for c in response.context_items])
            with st.expander("Reasoning Steps"):
                st.write(response.reasoning_steps)

        st.session_state.iperform_chat_history.append({"role": "assistant", "content": response.answer})

    st.divider()
    st.subheader("Conversation History")
    st.dataframe(chat_service.history(scope_id=scope_id, limit=50), use_container_width=True)
