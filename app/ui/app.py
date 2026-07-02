from __future__ import annotations
import streamlit as st
from app.config.constants import APP_DISPLAY_NAME, CORE_CAPABILITIES, HIERARCHY_LEVELS, PERSONAS, TIME_PERIODS
from app.config.settings import get_settings
from app.ui.pages.ai_assistant_chat import render_ai_assistant_chat_page
from app.ui.pages.insights_coaching import render_insights_coaching_page
from app.ui.pages.feedback_learning import render_feedback_learning_page
from app.ui.pages.recommendation_engine import render_recommendation_engine_page
from app.ui.pages.opportunity_engine import render_opportunity_engine_page
from app.ui.pages.prediction_engine import render_prediction_engine_page
from app.ui.pages.embedding_similarity import render_embedding_similarity_page
from app.ui.pages.feature_store import render_feature_store_page
from app.ui.pages.memory_timeline import render_memory_timeline_page
from app.ui.pages.knowledge_management import render_knowledge_management_page
from app.ui.pages.data_ingestion_sync import render_data_ingestion_sync_page
from app.ui.widgets.runtime_status import render_runtime_status_panel

settings = get_settings()

st.set_page_config(page_title=APP_DISPLAY_NAME, page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title(APP_DISPLAY_NAME)
st.sidebar.caption("Enterprise demo foundation")
persona = st.sidebar.selectbox("Persona", PERSONAS, index=3)
hierarchy_level = st.sidebar.selectbox("Hierarchy Level", HIERARCHY_LEVELS, index=4)
time_period = st.sidebar.selectbox("Time Period", TIME_PERIODS, index=2)

st.title(APP_DISPLAY_NAME)
st.caption("Part 11.0.1 — Final Folder Structure + UV Configuration + Environment Framework")
st.info("This is the foundation shell. Business pages will be added in later rebuild parts.")

c1, c2, c3 = st.columns(3)
c1.metric("Persona", persona)
c2.metric("Hierarchy", hierarchy_level)
c3.metric("Period", time_period)

st.subheader("Locked Capabilities")
st.write(", ".join(CORE_CAPABILITIES))

st.subheader("Runtime Configuration")
st.json({
    "app_env": settings.app_env,
    "graph_name": settings.tigergraph_graph,
    "schema_prefix": settings.tigergraph_schema_prefix,
    "sqlite_db_path": settings.sqlite_db_path,
    "chroma_path": settings.chroma_path,
    "tigergraph_mcp_enabled": settings.enable_tigergraph_mcp,
    "tigergraph_rest_fallback_enabled": settings.enable_tigergraph_rest_fallback,
})


render_runtime_status_panel()


st.divider()
with st.expander("Data Ingestion & Sync Preview", expanded=False):
    render_data_ingestion_sync_page()


st.divider()
with st.expander("Knowledge Management & RAG Preview", expanded=False):
    render_knowledge_management_page()


st.divider()
with st.expander("Context Graph & Temporal Memory Preview", expanded=False):
    render_memory_timeline_page()


st.divider()
with st.expander("Feature Store Preview", expanded=False):
    render_feature_store_page()


st.divider()
with st.expander("Graph Embeddings & Similarity Preview", expanded=False):
    render_embedding_similarity_page()


st.divider()
with st.expander("Prediction Engine Preview", expanded=False):
    render_prediction_engine_page()


st.divider()
with st.expander("Opportunity Engine Preview", expanded=False):
    render_opportunity_engine_page()


st.divider()
with st.expander("Recommendation Engine Preview", expanded=False):
    render_recommendation_engine_page()


st.divider()
with st.expander("Feedback Learning Preview", expanded=False):
    render_feedback_learning_page()


st.divider()
with st.expander("AI Insights & Coaching Preview", expanded=True):
    render_insights_coaching_page()


st.divider()
with st.expander("AI Assistant Chat Preview", expanded=True):
    render_ai_assistant_chat_page()
