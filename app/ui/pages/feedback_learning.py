from __future__ import annotations

import streamlit as st

from app.models.feedback_learning import FeedbackAction, FeedbackActor, FeedbackSearchRequest, FeedbackSubmitRequest, OutcomeType
from app.models.recommendations import RecommendationRunRequest, RecommendationSearchRequest
from app.services.feedback_learning_service import FeedbackLearningService
from app.services.recommendation_service import RecommendationService


def render_feedback_learning_page() -> None:
    st.title("Feedback Learning")
    st.caption("Capture recommendation accept/reject/complete outcomes and convert them into learning signals and memory updates.")

    feedback_service = FeedbackLearningService()
    rec_service = RecommendationService()

    tab_submit, tab_history, tab_learning, tab_counts = st.tabs(["Submit Feedback", "Feedback History", "Learning Signals", "Counts"])

    with tab_submit:
        st.write("Generate recommendations first if no recommendation ID is available.")
        if st.button("Generate Sample Recommendations"):
            result = rec_service.run_recommendations(RecommendationRunRequest(write_to_tigergraph=False, limit=25))
            st.json(result.model_dump())

        recs = rec_service.list_recommendations(RecommendationSearchRequest(limit=25))
        rec_ids = [r["recommendation_id"] for r in recs]
        selected_rec = st.selectbox("Recommendation", rec_ids) if rec_ids else st.text_input("Recommendation ID")
        actor = st.selectbox("Actor", [a.value for a in FeedbackActor])
        action = st.selectbox("Action", [a.value for a in FeedbackAction])
        reason = st.text_area("Reason", value="Demo feedback from user.")
        outcome_enabled = st.checkbox("Add outcome", value=True)
        outcome_type = None
        outcome_value = None
        outcome_summary = None
        if outcome_enabled:
            outcome_type = OutcomeType(st.selectbox("Outcome Type", [o.value for o in OutcomeType]))
            outcome_value = st.number_input("Outcome Value", value=25000.0)
            outcome_summary = st.text_area("Outcome Summary", value="Simulated business outcome from accepted recommendation.")
        write = st.checkbox("Write to TigerGraph", value=False)

        if st.button("Submit Feedback"):
            with st.status("Submitting feedback and generating learning signal...", expanded=True) as status:
                result = feedback_service.submit_feedback(
                    FeedbackSubmitRequest(
                        recommendation_id=selected_rec,
                        actor=FeedbackActor(actor),
                        action=FeedbackAction(action),
                        reason=reason,
                        outcome_type=outcome_type,
                        outcome_value=outcome_value,
                        outcome_summary=outcome_summary,
                        write_to_tigergraph=write,
                    )
                )
                st.success("Feedback submitted and learning signal generated")
                st.json(result.model_dump())
                status.update(label="Feedback learning complete", state="complete")

    with tab_history:
        st.dataframe(feedback_service.list_feedback(FeedbackSearchRequest(limit=200)), use_container_width=True)

    with tab_learning:
        st.dataframe(feedback_service.list_learning_signals(200), use_container_width=True)

    with tab_counts:
        st.dataframe(feedback_service.counts(), use_container_width=True)
