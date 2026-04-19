"""
streamlit_app.py
----------------
Main Streamlit entry point for Utility Billing AI.
"""

import sys
import os
from pathlib import Path
import requests

def _add_path_front(p: Path):
    p_str = str(p)
    if p_str and p.exists():
        if p_str in sys.path:
            sys.path.remove(p_str)
        sys.path.insert(0, p_str)

_THIS_FILE = Path(__file__).resolve()
project_root = _THIS_FILE.parent.parent

_add_path_front(project_root)
_add_path_front(project_root / "src")

env_root = os.environ.get("UTIL_BILLING_PROJECT_ROOT")
if env_root:
    _add_path_front(Path(env_root).expanduser().resolve())
    _add_path_front(Path(env_root).expanduser().resolve() / "src")

# -----------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(str(project_root / ".env"))
except:
    pass

# -----------------------------------------------------
# LOAD LOGGER
# -----------------------------------------------------
try:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

import streamlit as st

# -----------------------------------------------------
# PAGE SETTINGS (MUST BE FIRST STREAMLIT COMMAND)
# -----------------------------------------------------
st.set_page_config(
    page_title="Utility Billing AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from app.components.home import check_authentication, logout
from app.components.login import render_login_page
from app.components.portal import render_portal
from app.components.dashboard import render_dashboard
from app.components.usage_metrics import render as render_usage_metrics

# -----------------------------------------------------
# CHECK BACKEND READINESS (ONCE PER SESSION)
# -----------------------------------------------------
@st.cache_resource
def initialize_backend():
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    try:
        response = requests.get(f"{api_base_url}/api/v1/health/ready", timeout=10)
        response.raise_for_status()
        logger.info("✅ Backend is ready")
    except Exception as e:
        logger.warning(f"⚠️ Backend readiness check failed: {e}")

initialize_backend()

# -----------------------------------------------------
# AUTHENTICATION CHECK
# -----------------------------------------------------
if not check_authentication():
    render_login_page()
    st.stop()

# -----------------------------------------------------
# SERVICE PORTAL (shown once after login, before dashboard)
# -----------------------------------------------------
if "selected_service" not in st.session_state:
    render_portal()
    st.stop()

# -----------------------------------------------------
# USER INFO + LOGOUT
# -----------------------------------------------------
if "username" in st.session_state:
    st.markdown("""
        <style>
        div[data-testid="column"]:has(button[data-testid*="baseButton-secondary"]) button {
            border: 2px solid #ff4b4b !important;
            border-radius: 8px !important;
            background-color: transparent !important;
            color: #ff4b4b !important;
            font-weight: 600 !important;
        }
        div[data-testid="column"]:has(button[data-testid*="baseButton-secondary"]) button:hover {
            background-color: #ff4b4b !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2.2, 0.7, 0.5, 0.3])

    with col4:
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()

    with col3:
        st.markdown(
            f"<div style='text-align: right; margin-top: 8px; font-size: 12px;'>"
            f"{st.session_state.username}</div>",
            unsafe_allow_html=True
        )

    with col2:
        if st.button("🏠 Home", key="portal_btn", use_container_width=True):
            st.session_state.pop("selected_service", None)
            st.session_state.nav_state = "home"
            st.rerun()

# -----------------------------------------------------
# LOAD CUSTOM CSS
# -----------------------------------------------------
css_path = project_root / "app/assets/sidebar_styles.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    logger.warning(f"CSS file not found: {css_path}")

# -----------------------------------------------------
# SIDEBAR LOGO
# -----------------------------------------------------
try:
    logo_path = (project_root / "app/assets/logo.jpeg").resolve()
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=140)
    else:
        st.sidebar.write("Troy & Banks")
except Exception as e:
    logger.error(f"Error loading logo: {e}")
    st.sidebar.write("Troy & Banks")

st.sidebar.title("Troy & Banks – Utility Billing AI")
st.sidebar.markdown("---")

# -----------------------------------------------------
# PAGE ICONS (UPDATED WITH SAVINGS)
# -----------------------------------------------------
page_icons = {
    "Upload & Ingest": "📁",
    "Audit Bills": "📄",
    "Manage Tariffs": "📑",
    "Pipeline Status": "📊",
    "Generate Reports": "📋",
    "Savings Analysis": "💰",   # ← NEW
    "Upload History": "📜",
    "Usage Metrics": "📈",
}

# -----------------------------------------------------
# TOOLTIP SUPPORT
# -----------------------------------------------------
st.sidebar.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const labels = {
        '📁': 'Upload & Ingest',
        '📄': 'Audit Bills',
        '📊': 'Pipeline Status',
        '📋': 'Generate Reports',
        '📑': 'Manage Tariffs',
        '💰': 'Savings Analysis',
        '📜': 'Upload History',
        '📈': 'Usage Metrics',
    };
    setTimeout(() => {
        document.querySelectorAll('[data-baseweb="radio"] label').forEach(label => {
            const icon = label.textContent.trim().substring(0, 2);
            if (labels[icon]) {
                label.setAttribute('title', labels[icon]);
            }
        });
    }, 100);
});
</script>
""", unsafe_allow_html=True)

page_options = list(page_icons.keys())

# -----------------------------------------------------
# NAVIGATION STATE
# -----------------------------------------------------
if "nav_state" not in st.session_state:
    st.session_state.nav_state = "home"

show_home = st.session_state.nav_state == "home"

if not show_home:
    st.sidebar.markdown("### 📍 Navigation")

    default_index = (
        page_options.index(st.session_state.nav_state)
        if st.session_state.nav_state in page_options else 0
    )

    selected_page = st.sidebar.radio(
        "Pages",
        page_options,
        index=default_index,
        format_func=lambda x: f"{page_icons[x]}  {x}",
        label_visibility="collapsed"
    )

    if selected_page != st.session_state.nav_state:
        st.session_state.nav_state = selected_page

    st.sidebar.markdown("---")

    if st.sidebar.button("🏠 Back to Home", use_container_width=True):
        st.session_state.nav_state = "home"
        st.rerun()

    page = selected_page
else:
    page = None

# -----------------------------------------------------
# HOME DASHBOARD
# -----------------------------------------------------
if show_home:
    render_dashboard()
    st.stop()

# -----------------------------------------------------
# ROUTING
# -----------------------------------------------------
if page == "Upload & Ingest":
    from app.components.file_uploader import render_file_uploader
    render_file_uploader()

elif page == "Audit Bills":
    from app.components.user_bills_viewer import render_user_bills_viewer
    render_user_bills_viewer()

elif page == "Manage Tariffs":
    from app.components.tariff_details_viewer import render_tariff_details_viewer
    render_tariff_details_viewer()

elif page == "Pipeline Status":
    st.title("📊 Pipeline Status")
    st.markdown("---")
    st.markdown("""
        <div style="display:flex;align-items:center;justify-content:center;
                    height:500px;flex-direction:column;gap:20px;">
            <div style="font-size:120px;">🚀</div>
            <h1>Coming Soon</h1>
            <p>Pipeline monitoring is under development.</p>
        </div>
    """, unsafe_allow_html=True)

elif page == "Generate Reports":
    from app.components.reports_viewer import render_report_viewer
    render_report_viewer()

elif page == "Savings Analysis":
    from app.components.savings import render_savings
    render_savings()

elif page == "Upload History":
    from app.components.upload_history import render_upload_history
    render_upload_history()
elif page == "Usage Metrics":
    render_usage_metrics()

# -----------------------------------------------------
# FOOTER
# -----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.caption("© 2025 Troy & Banks | Utility Billing AI Prototype")
