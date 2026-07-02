from __future__ import annotations

import streamlit as st


def render_header(page_title: str) -> None:
    persona = st.session_state.get("selected_persona", "Advisor")
    scope_type = st.session_state.get("selected_scope_type", "Advisor")
    scope_id = st.session_state.get("selected_scope_id", "ADV0001")
    period = st.session_state.get("selected_time_period", "YTD")

    st.markdown(f'<div class="iperform-title">{page_title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="iperform-subtitle">Persona: <b>{persona}</b> • Scope: <b>{scope_type} {scope_id}</b> • Period: <b>{period}</b></div>',
        unsafe_allow_html=True,
    )
