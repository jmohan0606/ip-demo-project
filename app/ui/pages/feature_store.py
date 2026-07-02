from __future__ import annotations

import streamlit as st

from app.models.features import FeatureGroupName, FeatureMaterializationRequest
from app.services.feature_store_service import FeatureStoreService


def render_feature_store_page() -> None:
    st.title("Feature Engineering & Feature Store")
    st.caption("Materialize local SQLite feature vectors from enterprise demo data.")

    service = FeatureStoreService()

    tab_materialize, tab_vectors, tab_counts = st.tabs(["Materialize", "Vectors", "Counts"])

    with tab_materialize:
        selected = st.multiselect("Feature Groups", [g.value for g in FeatureGroupName], default=[
            FeatureGroupName.ADVISOR_GROWTH.value,
            FeatureGroupName.CRM_ACTIVITY.value,
            FeatureGroupName.AGP_PROGRESS.value,
        ])
        if st.button("Materialize Features"):
            groups = [FeatureGroupName(g) for g in selected]
            with st.status("Materializing feature vectors...", expanded=True) as status:
                results = service.materialize(FeatureMaterializationRequest(feature_groups=groups))
                for result in results:
                    st.write(result.model_dump())
                status.update(label="Feature materialization complete", state="complete")

    with tab_vectors:
        feature_group = st.selectbox("Feature Group", [""] + [g.value for g in FeatureGroupName])
        data = service.list_vectors(feature_group or None, limit=200)
        st.dataframe(data, use_container_width=True)

    with tab_counts:
        st.dataframe(service.counts(), use_container_width=True)
