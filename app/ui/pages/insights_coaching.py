from __future__ import annotations

import streamlit as st

from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.services.insights_coaching_service import InsightsCoachingService


def render_insights_coaching_page() -> None:
    st.title("AI Insights & Coaching Engine")
    st.caption("Unified insight cards and coaching plan using features, predictions, opportunities, recommendations, memory and documents.")

    service = InsightsCoachingService()

    scope_type = st.selectbox("Scope Type", [s.value for s in InsightScopeType], index=4)
    scope_id = st.text_input("Scope ID", value="ADV0001")
    persona = st.selectbox("Persona", ["Advisor", "MDW", "DDW", "Firm"], index=0)
    time_period = st.selectbox("Time Period", ["MTD", "QTD", "YTD", "Last 12 Months"], index=2)
    question = st.text_input("Question", value="What should I focus on this week?")
    write = st.checkbox("Write to TigerGraph", value=False)
    write_memory = st.checkbox("Write insight to memory", value=True)

    if st.button("Generate Insights & Coaching"):
        with st.status("Generating insights and coaching plan...", expanded=True) as status:
            payload = service.generate_dashboard_payload(
                InsightRequest(
                    scope_type=InsightScopeType(scope_type),
                    scope_id=scope_id,
                    persona=persona,
                    time_period=time_period,
                    question=question,
                    write_to_tigergraph=write,
                    write_to_memory=write_memory,
                )
            )
            st.subheader("Executive Summary")
            st.info(payload.executive_summary)

            cols = st.columns(2)
            for idx, card in enumerate(payload.cards):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"### {card.title}")
                        st.caption(f"{card.card_type.value} | Severity: {card.severity} | Confidence: {card.confidence}")
                        st.write(card.summary)
                        with st.expander("Evidence & Reasoning"):
                            st.write("Evidence")
                            st.json([e.model_dump() for e in card.evidence])
                            st.write("Reasoning Steps")
                            st.write(card.reasoning_steps)
                            st.write("Recommended Actions")
                            st.write(card.recommended_actions)

            if payload.coaching_plan:
                st.subheader("Coaching Plan")
                st.write(payload.coaching_plan.summary)
                st.write("Focus Areas:", payload.coaching_plan.focus_areas)
                st.write("Next Best Actions:", payload.coaching_plan.next_best_actions)
                st.write("Manager Review Notes:", payload.coaching_plan.manager_review_notes)

            if payload.context_summary:
                with st.expander("Context Memory Used"):
                    st.text(payload.context_summary)

            status.update(label="Insights generated", state="complete")

    st.subheader("Generated Insight History")
    st.dataframe(service.list_cards(scope_id=scope_id, limit=50), use_container_width=True)
