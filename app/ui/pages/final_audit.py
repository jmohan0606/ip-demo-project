from __future__ import annotations

import streamlit as st

from app.services.final_audit_service import FinalAuditService


def render_final_audit_page() -> None:
    st.title("Final Audit & Gap Closure")
    st.caption("Runs production-readiness checks across requirements, agents, MCP, UI, SQLite, Chroma and documentation.")

    if st.button("Run Final Audit"):
        with st.status("Running final audit...", expanded=True) as status:
            report = FinalAuditService().run_audit()
            summary = report["summary"]
            st.metric("Overall Status", summary["overall_status"])
            st.metric("Requirements Passed", f"{summary['requirements_passed']} / {summary['requirement_count']}")
            st.json(summary)

            st.subheader("Requirement Traceability")
            st.dataframe(report["requirements"], use_container_width=True)

            st.subheader("SQLite")
            st.json(report["sqlite"])

            st.subheader("Chroma")
            st.json(report["chroma"])

            st.subheader("Graph Access")
            st.json(report["graph_access"])

            status.update(label="Final audit complete", state="complete")
