from __future__ import annotations

from app.ui.styles.theme import apply_enterprise_theme
from app.ui.state.session_state import init_session_state
from app.ui.components.navigation import render_sidebar_navigation
from app.ui.components.header import render_header

from app.ui.pages.enterprise_dashboard import render_enterprise_dashboard_page
from app.ui.pages.final_audit import render_final_audit_page
from app.ui.pages.runtime_validation import render_runtime_validation_page
from app.ui.pages.deep_hardening import render_deep_hardening_page
from app.ui.pages.agentic_ai_console import render_agentic_ai_console_page
from app.ui.pages.graph_access_status import render_graph_access_status_page
from app.ui.pages.end_to_end_demo_run import render_end_to_end_demo_run_page
from app.ui.pages.advisor_360 import render_advisor_360_page
from app.ui.pages.agp_goals_coaching import render_agp_goals_coaching_page
from app.ui.pages.opportunity_engine import render_opportunity_engine_page
from app.ui.pages.recommendation_engine import render_recommendation_engine_page
from app.ui.pages.feedback_learning import render_feedback_learning_page
from app.ui.pages.feature_store import render_feature_store_page
from app.ui.pages.embedding_similarity import render_embedding_similarity_page
from app.ui.pages.prediction_engine import render_prediction_engine_page
from app.ui.pages.knowledge_management import render_knowledge_management_page
from app.ui.pages.memory_timeline import render_memory_timeline_page
from app.ui.pages.data_ingestion_sync import render_data_ingestion_sync_page
from app.ui.pages.ai_assistant_chat import render_ai_assistant_chat_page
from app.ui.widgets.runtime_status import render_runtime_status_panel


def main() -> None:
    apply_enterprise_theme()
    init_session_state()
    page = render_sidebar_navigation()
    render_header(page)

    if page == "Executive Dashboard":
        render_enterprise_dashboard_page()
    elif page == "Final Audit & Gap Closure":
        render_final_audit_page()
    elif page == "Final Runtime Validation":
        render_runtime_validation_page()
    elif page == "Deep Runtime Hardening":
        render_deep_hardening_page()
    elif page == "Agentic AI Console":
        render_agentic_ai_console_page()
    elif page == "End-to-End Demo Run":
        render_end_to_end_demo_run_page()
    elif page == "Advisor 360":
        render_advisor_360_page()
    elif page == "AGP Goals & Coaching":
        render_agp_goals_coaching_page()
    elif page == "Opportunities":
        render_opportunity_engine_page()
    elif page == "Recommendations":
        render_recommendation_engine_page()
    elif page == "Feedback Learning":
        render_feedback_learning_page()
    elif page == "Feature Store":
        render_feature_store_page()
    elif page == "Graph Embeddings & Similarity":
        render_embedding_similarity_page()
    elif page == "Predictions":
        render_prediction_engine_page()
    elif page == "Knowledge Management":
        render_knowledge_management_page()
    elif page == "Context Memory":
        render_memory_timeline_page()
    elif page == "Data Ingestion & Sync":
        render_data_ingestion_sync_page()
    elif page == "AI Assistant Chat":
        render_ai_assistant_chat_page()
    elif page == "Graph Access Status":
        render_graph_access_status_page()
    elif page == "Runtime Status":
        render_runtime_status_panel()


if __name__ == "__main__":
    main()
