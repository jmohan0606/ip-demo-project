from __future__ import annotations

import streamlit as st

from app.services.demo_orchestration_service import DemoOrchestrationService


def render_end_to_end_demo_run_page() -> None:
    st.title("End-to-End Demo Run")
    st.caption("Runs the complete local demo pipeline from knowledge ingestion to coaching insights.")

    advisor_id = st.text_input("Advisor ID", value="ADV0001")
    if st.button("Run Full Demo Pipeline"):
        with st.status("Running full iPerform demo pipeline...", expanded=True) as status:
            result = DemoOrchestrationService().run_full_demo(advisor_id)
            for step in result.steps:
                st.write(f"{step.step_name}: {step.status} — {step.message} ({step.records})")
            st.json(result.summary)
            status.update(
                label="Full demo pipeline complete" if result.status == "completed" else "Full demo pipeline failed",
                state="complete" if result.status == "completed" else "error",
            )
