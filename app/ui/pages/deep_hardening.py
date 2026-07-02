from __future__ import annotations

import streamlit as st

from app.services.deep_hardening_service import DeepHardeningService


def render_deep_hardening_page() -> None:
    st.title("Deep Runtime Hardening")
    st.caption("Validates native LangGraph collaboration, real Chroma persistence, MCP usage, UI progress, upload resume, and wealth-management scenario coverage.")

    if st.button("Run Deep Hardening Validation"):
        with st.status("Running deep hardening checks...", expanded=True) as status:
            report = DeepHardeningService().run()
            st.metric("Overall Status", report["overall_status"])
            if report["failed_items"]:
                st.error(f"Failed items: {report['failed_items']}")
            else:
                st.success("All deep hardening checks passed.")
            if report["full_coverage_notes"]:
                st.warning(report["full_coverage_notes"])
            st.json(report)
            status.update(label="Deep hardening complete", state="complete" if report["overall_status"] == "passed" else "error")
