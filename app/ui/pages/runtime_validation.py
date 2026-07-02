from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.runtime_validation_service import RuntimeValidationService


def render_runtime_validation_page() -> None:
    st.title("Final Runtime Validation")
    st.caption("Runs app-level runtime checks across API imports, UI wiring, SQLite, Chroma, graph access, agents, recommendations, feedback, memory and chat.")

    if st.button("Run Runtime Validation"):
        with st.status("Running runtime validation checks...", expanded=True) as status:
            report = RuntimeValidationService().run()
            st.metric("Status", report["status"])
            st.metric("Passed", report["checks_passed"])
            st.metric("Failed", report["checks_failed"])

            rows = [
                {
                    "check": r["check_name"],
                    "status": r["status"],
                    "message": r["message"],
                }
                for r in report["results"]
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            with st.expander("Full Runtime Report"):
                st.json(report)

            status.update(
                label="Runtime validation complete",
                state="complete" if report["status"] == "passed" else "error",
            )
