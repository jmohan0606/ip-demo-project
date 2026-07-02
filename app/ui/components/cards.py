from __future__ import annotations

import streamlit as st


def metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="card-caption">{label}</div>
            <div style="font-size:1.45rem;font-weight:750;">{value}</div>
            <div class="card-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(title: str, summary: str, severity: str = "Medium", confidence: float | None = None) -> None:
    conf = "" if confidence is None else f" • Confidence {confidence}"
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="card-title">{title}</div>
            <span class="status-pill">{severity}{conf}</span>
            <p style="margin-top:.75rem;">{summary}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
