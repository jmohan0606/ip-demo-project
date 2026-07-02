from __future__ import annotations

import streamlit as st

from app.models.recommendations import RecommendationActionRequest, RecommendationRunRequest, RecommendationSearchRequest, RecommendationStatus, RecommendationType
from app.services.recommendation_service import RecommendationService


def render_recommendation_engine_page() -> None:
    st.title("Recommendation Engine")
    st.caption("Generate explainable, playbook-supported and compliance-checked advisor recommendations.")

    service = RecommendationService()
    tab_run, tab_search, tab_action, tab_counts = st.tabs(["Run", "Search", "Accept/Reject", "Counts"])

    with tab_run:
        entity_id = st.text_input("Advisor ID optional", value="")
        min_score = st.slider("Minimum Opportunity Score", 0.0, 1.0, 0.45)
        limit = st.slider("Limit", 10, 1000, 250)
        write = st.checkbox("Write to TigerGraph", value=False)
        if st.button("Run Recommendation Engine"):
            with st.status("Generating recommendations...", expanded=True) as status:
                result = service.run_recommendations(
                    RecommendationRunRequest(
                        entity_id=entity_id or None,
                        write_to_tigergraph=write,
                        min_opportunity_score=min_score,
                        limit=limit,
                    )
                )
                st.json(result.model_dump())
                status.update(label="Recommendation generation complete", state="complete")

    with tab_search:
        advisor_id = st.text_input("Search Advisor ID", value="ADV0001")
        rtype = st.selectbox("Recommendation Type", [""] + [r.value for r in RecommendationType])
        rows = service.list_recommendations(
            RecommendationSearchRequest(
                entity_id=advisor_id or None,
                recommendation_type=RecommendationType(rtype) if rtype else None,
                limit=100,
            )
        )
        st.dataframe(rows, use_container_width=True)

        if rows:
            with st.expander("Explainability for top recommendation", expanded=True):
                top = rows[0]
                st.write("Action:", top["action_text"])
                st.write("Rationale:", top["rationale"])
                st.write("Compliance:", top["compliance_status"])
                st.write("Supporting Documents:", top["supporting_documents"])
                st.write("Evidence:", top["evidence"])
                st.write("Reasoning Steps:", top["reasoning_steps"])

    with tab_action:
        rec_id = st.text_input("Recommendation ID")
        status_value = st.selectbox("New Status", [s.value for s in RecommendationStatus])
        reason = st.text_area("Reason", value="")
        if st.button("Update Recommendation Status"):
            updated = service.update_status(
                RecommendationActionRequest(
                    recommendation_id=rec_id,
                    status=RecommendationStatus(status_value),
                    reason=reason or None,
                )
            )
            st.success("Recommendation status updated")
            st.json(updated)

    with tab_counts:
        st.dataframe(service.counts(), use_container_width=True)
