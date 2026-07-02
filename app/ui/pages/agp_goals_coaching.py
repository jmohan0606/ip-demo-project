from __future__ import annotations

import streamlit as st

from app.services.feature_store_service import FeatureStoreService
from app.models.features import FeatureMaterializationRequest


def render_agp_goals_coaching_page() -> None:
    advisor_id = st.session_state.get("selected_scope_id", "ADV0001")
    st.caption("AGP goal tracking and coaching is advisor-specific. Non-AGP or non-advisor scopes can still review aggregate signals.")

    if st.button("Materialize AGP Features"):
        FeatureStoreService().materialize(FeatureMaterializationRequest())
        st.success("AGP features materialized.")

    agp = FeatureStoreService().get_vector("Advisor", advisor_id, "agp_progress_features")
    if agp:
        st.subheader("AGP KPI Status")
        features = agp["features"]
        cols = st.columns(4)
        cols[0].metric("Goals", features.get("goal_count", 0))
        cols[1].metric("KPIs", features.get("kpi_count", 0))
        cols[2].metric("Off Track", features.get("off_track_kpi_count", 0))
        cols[3].metric("Avg Attainment %", features.get("avg_goal_attainment_pct", 0))
        st.json(features)
    else:
        st.info("No AGP features found for selected advisor.")
