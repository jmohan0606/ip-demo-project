from __future__ import annotations

import streamlit as st


PAGES = [
    "Executive Dashboard",
    "Final Audit & Gap Closure",
    "Final Runtime Validation",
    "Deep Runtime Hardening",
    "Agentic AI Console",
    "End-to-End Demo Run",
    "Advisor 360",
    "AGP Goals & Coaching",
    "Opportunities",
    "Recommendations",
    "Feedback Learning",
    "Feature Store",
    "Graph Embeddings & Similarity",
    "Predictions",
    "Knowledge Management",
    "Context Memory",
    "Data Ingestion & Sync",
    "AI Assistant Chat",
    "Graph Access Status",
    "Runtime Status",
]


def render_sidebar_navigation() -> str:
    st.sidebar.markdown("## iPerform Insights & Coaching")
    st.sidebar.caption("Enterprise local demo")

    page = st.sidebar.radio("Navigation", PAGES, key="enterprise_selected_page")

    st.sidebar.divider()
    st.sidebar.subheader("Persona & Scope")

    persona = st.sidebar.selectbox("Persona", ["Advisor", "MDW", "DDW", "Firm"], index=0)
    scope_options = {
        "Advisor": ["Advisor"],
        "MDW": ["Market", "Advisor"],
        "DDW": ["Division", "Region", "Market", "Advisor"],
        "Firm": ["Firm", "Division", "Region", "Market", "Advisor"],
    }
    scope_type = st.sidebar.selectbox("Scope Type", scope_options.get(persona, ["Advisor"]))

    default_scope = {
        "Firm": "FIRM001",
        "Division": "DIV01",
        "Region": "REG0101",
        "Market": "MKT010101",
        "Advisor": "ADV0001",
    }.get(scope_type, "ADV0001")

    scope_id = st.sidebar.text_input("Scope ID", value=default_scope)
    time_period = st.sidebar.selectbox("Time Period", ["MTD", "QTD", "YTD", "Last 12 Months", "Last 24 Months", "Custom"], index=2)

    st.session_state.selected_persona = persona
    st.session_state.selected_scope_type = scope_type
    st.session_state.selected_scope_id = scope_id
    st.session_state.selected_time_period = time_period

    st.sidebar.divider()
    st.sidebar.caption("Loading overlays and progress indicators are enabled in each execution page.")
    return page
