from __future__ import annotations
import streamlit as st
from app.services.runtime_status_service import RuntimeStatusService

def render_runtime_status_panel() -> None:
    report = RuntimeStatusService().get_health_report()
    st.subheader("Runtime Status")
    st.caption(f"Overall status: {report.overall_status}")
    for component in report.components:
        with st.expander(f"{component.component_name} — {component.status}", expanded=False):
            st.write(f"Configured: {component.configured}")
            st.write(component.detail or "No details")
