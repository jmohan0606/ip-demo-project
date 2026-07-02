from __future__ import annotations

import streamlit as st


DEFAULTS = {
    "selected_persona": "Advisor",
    "selected_scope_type": "Advisor",
    "selected_scope_id": "ADV0001",
    "selected_time_period": "YTD",
    "selected_page": "Executive Dashboard",
    "loading_message": "",
}


def init_session_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_scope(persona: str, scope_type: str, scope_id: str, time_period: str) -> None:
    st.session_state.selected_persona = persona
    st.session_state.selected_scope_type = scope_type
    st.session_state.selected_scope_id = scope_id
    st.session_state.selected_time_period = time_period
