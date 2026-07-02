from __future__ import annotations

import streamlit as st

from app.models.predictions import PredictionRunRequest, PredictionSearchRequest, PredictionType
from app.services.prediction_service import PredictionService


def render_prediction_engine_page() -> None:
    st.title("Prediction Engine")
    st.caption("Run local sklearn demo predictions for revenue, NNM, AUM, AGP risk, advisor success and opportunity propensity.")

    service = PredictionService()
    tab_run, tab_search, tab_counts, tab_models = st.tabs(["Run", "Search", "Counts", "Models"])

    with tab_run:
        selected = st.multiselect("Prediction Types", [p.value for p in PredictionType], default=[p.value for p in PredictionType])
        write = st.checkbox("Write to TigerGraph", value=False)
        if st.button("Run Predictions"):
            with st.status("Running prediction engine...", expanded=True) as status:
                result = service.run_predictions(
                    PredictionRunRequest(
                        prediction_types=[PredictionType(p) for p in selected],
                        write_to_tigergraph=write,
                    )
                )
                st.json(result.model_dump())
                status.update(label="Predictions complete", state="complete")

    with tab_search:
        advisor_id = st.text_input("Advisor ID", value="ADV0001")
        ptype = st.selectbox("Prediction Type", [""] + [p.value for p in PredictionType])
        rows = service.list_predictions(
            PredictionSearchRequest(
                entity_id=advisor_id or None,
                prediction_type=PredictionType(ptype) if ptype else None,
                limit=100,
            )
        )
        st.dataframe(rows, use_container_width=True)

    with tab_counts:
        st.dataframe(service.counts(), use_container_width=True)

    with tab_models:
        st.dataframe(service.model_metadata(), use_container_width=True)
