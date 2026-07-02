from __future__ import annotations

import streamlit as st

from app.services.feature_store_service import FeatureStoreService
from app.services.prediction_service import PredictionService
from app.services.opportunity_service import OpportunityService
from app.services.recommendation_service import RecommendationService
from app.models.predictions import PredictionSearchRequest
from app.models.opportunities import OpportunitySearchRequest
from app.models.recommendations import RecommendationSearchRequest


def render_advisor_360_page() -> None:
    advisor_id = st.session_state.get("selected_scope_id", "ADV0001")
    st.caption("Advisor-level view of feature, prediction, opportunity and recommendation signals.")

    features = FeatureStoreService().get_vector("Advisor", advisor_id, "advisor_growth_features")
    if features:
        st.subheader("Advisor Growth Feature Vector")
        st.json(features["features"])
    else:
        st.warning("Feature vector not found. Materialize features from the Feature Store page.")

    tabs = st.tabs(["Predictions", "Opportunities", "Recommendations"])
    with tabs[0]:
        st.dataframe(PredictionService().list_predictions(PredictionSearchRequest(entity_id=advisor_id, limit=100)), use_container_width=True)
    with tabs[1]:
        st.dataframe(OpportunityService().list_opportunities(OpportunitySearchRequest(entity_id=advisor_id, limit=100)), use_container_width=True)
    with tabs[2]:
        st.dataframe(RecommendationService().list_recommendations(RecommendationSearchRequest(entity_id=advisor_id, limit=100)), use_container_width=True)
