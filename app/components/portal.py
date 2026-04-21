"""
portal.py
---------
Service selection portal shown after login.
User picks NY Audit (stays in app) or VA Audit (redirects to VA service).
"""

import os
import streamlit as st
from app.components.home import logout


def render_portal():
    va_url = os.environ.get("VA_STREAMLIT_URL", "/va")

    # Logout button — top right
    if "username" in st.session_state:
        _, col_user, col_logout = st.columns([3.5, 0.5, 0.3])
        with col_logout:
            if st.button("Logout", key="portal_logout_btn", use_container_width=True):
                logout()
        with col_user:
            st.markdown(
                f"<div style='text-align: right; margin-top: 8px; font-size: 12px;'>"
                f"{st.session_state.username}</div>",
                unsafe_allow_html=True
            )

    st.markdown("""
        <style>
        .portal-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 60px 20px;
        }
        .portal-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
            text-align: center;
        }
        .portal-subtitle {
            font-size: 1rem;
            color: #888;
            margin-bottom: 48px;
            text-align: center;
        }
        .card-row {
            display: flex;
            gap: 32px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .audit-card {
            background: #1e1e2e;
            border: 2px solid #333;
            border-radius: 16px;
            padding: 40px 48px;
            text-align: center;
            cursor: pointer;
            transition: border-color 0.2s, transform 0.2s;
            min-width: 240px;
        }
        .audit-card:hover {
            border-color: #4f8ef7;
            transform: translateY(-4px);
        }
        .card-icon { font-size: 3rem; margin-bottom: 16px; }
        .card-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 6px; }
        .card-desc  { font-size: 0.9rem; color: #aaa; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="portal-container">
            <div class="portal-title">Troy & Banks — Utility Billing AI</div>
            <div class="portal-subtitle">Select the audit service you want to access</div>
        </div>
    """, unsafe_allow_html=True)

    col_gap, col_ny, col_va, col_gap2 = st.columns([1, 2, 2, 1])

    with col_ny:
        st.markdown("""
            <div class="audit-card">
                <div class="card-icon">🗽</div>
                <div class="card-title">New York Audit</div>
                <div class="card-desc">Utility bill auditing for New York state accounts</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open New York Audit", key="btn_ny", use_container_width=True, type="primary"):
            st.session_state.selected_service = "ny"
            st.rerun()

    with col_va:
        st.markdown("""
            <div class="audit-card">
                <div class="card-icon">🏛️</div>
                <div class="card-title">Virginia Audit</div>
                <div class="card-desc">Utility bill auditing for Virginia state accounts</div>
            </div>
        """, unsafe_allow_html=True)
        st.link_button("Open Virginia Audit", url=va_url, use_container_width=True)
