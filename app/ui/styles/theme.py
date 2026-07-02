from __future__ import annotations

import streamlit as st


def apply_enterprise_theme() -> None:
    st.set_page_config(
        page_title="iPerform Insights & Coaching",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .iperform-title {
            font-size: 1.65rem;
            font-weight: 750;
            margin-bottom: 0.15rem;
        }
        .iperform-subtitle {
            color: #667085;
            font-size: 0.92rem;
            margin-bottom: 1rem;
        }
        .metric-card {
            border: 1px solid #EAECF0;
            border-radius: 14px;
            padding: 1rem;
            background: #FFFFFF;
            box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .insight-card {
            border: 1px solid #D0D5DD;
            border-radius: 16px;
            padding: 1rem;
            background: #FFFFFF;
            min-height: 210px;
        }
        .card-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: .35rem;
        }
        .card-caption {
            color: #667085;
            font-size: .80rem;
        }
        .status-pill {
            display:inline-block;
            padding: .15rem .5rem;
            border-radius: 999px;
            border: 1px solid #D0D5DD;
            font-size: .75rem;
            color: #344054;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
