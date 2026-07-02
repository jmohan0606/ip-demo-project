from __future__ import annotations

import streamlit as st

from app.models.insights_coaching import InsightRequest, InsightScopeType
from app.models.predictions import PredictionRunRequest
from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.insights_coaching_service import InsightsCoachingService
from app.services.prediction_service import PredictionService
from app.services.recommendation_service import RecommendationService
from app.ui.components.cards import insight_card, metric_card


def _scope_type() -> InsightScopeType:
    value = st.session_state.get("selected_scope_type", "Advisor")
    return InsightScopeType(value)


def render_enterprise_dashboard_page() -> None:
    st.caption("Production-feel dashboard showing insights, coaching, recommendations and explainability in one view.")

    scope_type = _scope_type()
    scope_id = st.session_state.get("selected_scope_id", "ADV0001")
    persona = st.session_state.get("selected_persona", "Advisor")
    period = st.session_state.get("selected_time_period", "YTD")

    col_a, col_b, col_c = st.columns([1,1,1])
    with col_a:
        if st.button("Prepare Demo Signals", use_container_width=True):
            with st.status("Preparing predictions, opportunities and recommendations...", expanded=True) as status:
                PredictionService().run_predictions(PredictionRunRequest(write_to_tigergraph=False))
                RecommendationService().run_recommendations(
                    RecommendationRunRequest(
                        entity_id=scope_id if scope_type.value == "Advisor" else None,
                        write_to_tigergraph=False,
                        limit=100,
                    )
                )
                status.update(label="Demo signals prepared", state="complete")
    with col_b:
        generate = st.button("Generate Dashboard Insights", use_container_width=True)
    with col_c:
        st.button("Refresh Page", use_container_width=True)

    if generate:
        with st.status("Generating AI insight and coaching payload...", expanded=True) as status:
            payload = InsightsCoachingService().generate_dashboard_payload(
                InsightRequest(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    persona=persona,
                    time_period=period,
                    question="Generate dashboard insight and coaching plan.",
                    write_to_tigergraph=False,
                    write_to_memory=True,
                )
            )
            st.session_state.latest_dashboard_payload = payload.model_dump()
            status.update(label="Dashboard insights generated", state="complete")

    payload_data = st.session_state.get("latest_dashboard_payload")
    if not payload_data:
        st.info("Click **Prepare Demo Signals** and then **Generate Dashboard Insights** to populate the dashboard.")
        return

    st.subheader("Executive Summary")
    st.info(payload_data["executive_summary"])

    metrics = st.columns(4)
    with metrics[0]:
        metric_card("Insight Cards", str(len(payload_data["cards"])), "Generated for selected scope")
    with metrics[1]:
        high = sum(1 for c in payload_data["cards"] if c["severity"] == "High")
        metric_card("High Severity", str(high), "Needs review")
    with metrics[2]:
        recs = RecommendationService().list_recommendations(
            RecommendationSearchRequest(entity_id=scope_id if scope_type.value == "Advisor" else None, limit=100)
        )
        metric_card("Recommendations", str(len(recs)), "Available actions")
    with metrics[3]:
        metric_card("Memory", "Enabled", "Context graph write-back")

    st.subheader("Insights & Coaching Cards")
    cols = st.columns(2)
    for idx, card in enumerate(payload_data["cards"]):
        with cols[idx % 2]:
            insight_card(card["title"], card["summary"], card["severity"], card["confidence"])
            with st.expander("Evidence & Reasoning"):
                st.write("Evidence")
                st.json(card["evidence"])
                st.write("Reasoning")
                st.write(card["reasoning_steps"])
                st.write("Recommended Actions")
                st.write(card["recommended_actions"])

    if payload_data.get("coaching_plan"):
        st.subheader("Coaching Plan")
        plan = payload_data["coaching_plan"]
        c1, c2 = st.columns(2)
        with c1:
            st.write("Focus Areas")
            st.write(plan["focus_areas"])
            st.write("Next Best Actions")
            st.write(plan["next_best_actions"])
        with c2:
            st.write("Manager Review Notes")
            st.write(plan["manager_review_notes"])
            st.write("Advisor Talk Track")
            st.write(plan["advisor_talk_track"])

    if payload_data.get("context_summary"):
        with st.expander("Context Memory Used"):
            st.text(payload_data["context_summary"])
