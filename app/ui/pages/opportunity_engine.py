from __future__ import annotations

import streamlit as st

from app.models.opportunities import OpportunityPriority, OpportunityRunRequest, OpportunitySearchRequest, OpportunityType
from app.services.opportunity_service import OpportunityService


def render_opportunity_engine_page() -> None:
    st.title("Opportunity Engine")
    st.caption("Detect advisor opportunities using feature store, CRM, AGP, revenue, NNM and retention signals.")

    service = OpportunityService()
    tab_run, tab_search, tab_counts = st.tabs(["Run", "Search", "Counts"])

    with tab_run:
        entity_id = st.text_input("Advisor ID optional", value="")
        min_score = st.slider("Minimum Score", 0.0, 1.0, 0.45)
        limit = st.slider("Limit", 10, 1000, 250)
        write = st.checkbox("Write to TigerGraph", value=False)
        if st.button("Run Opportunity Detection"):
            with st.status("Detecting opportunities...", expanded=True) as status:
                result = service.run_opportunities(
                    OpportunityRunRequest(
                        entity_id=entity_id or None,
                        write_to_tigergraph=write,
                        min_score=min_score,
                        limit=limit,
                    )
                )
                st.json(result.model_dump())
                status.update(label="Opportunity detection complete", state="complete")

    with tab_search:
        advisor_id = st.text_input("Search Advisor ID", value="ADV0001")
        otype = st.selectbox("Opportunity Type", [""] + [o.value for o in OpportunityType])
        priority = st.selectbox("Priority", [""] + [p.value for p in OpportunityPriority])
        rows = service.list_opportunities(
            OpportunitySearchRequest(
                entity_id=advisor_id or None,
                opportunity_type=OpportunityType(otype) if otype else None,
                priority=OpportunityPriority(priority) if priority else None,
                limit=100,
            )
        )
        st.dataframe(rows, use_container_width=True)

    with tab_counts:
        st.dataframe(service.counts(), use_container_width=True)
