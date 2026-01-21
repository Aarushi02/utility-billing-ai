"""
streamlit_app.py
----------------
Main Streamlit entry point for Utility Billing AI.
"""

import sys
import os
from pathlib import Path

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

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(str(project_root / ".env"))
except:
    pass

# Load Logger
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
from app.components.dashboard import render_dashboard

# Initialize database on app startup
@st.cache_resource
def initialize_database():
    """Initialize database tables on first run."""
    try:
        from src.database.init_db import init_db
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"⚠️ Database initialization error: {e}")
        # Continue anyway - tables might already exist

# Call initialization once per session
initialize_database()

# -----------------------------------------------------
# AUTHENTICATION CHECK
# -----------------------------------------------------
if not check_authentication():
    render_login_page()
    st.stop()  # Stop execution if not authenticated

# Add user info and logout button in the top right corner
if "username" in st.session_state:
    # Add custom CSS for logout button
    st.markdown("""
        <style>
        div[data-testid="column"]:has(button[data-testid*="baseButton-secondary"]) button {
            border: 2px solid #ff4b4b !important;
            border-radius: 8px !important;
            background-color: transparent !important;
            color: #ff4b4b !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        div[data-testid="column"]:has(button[data-testid*="baseButton-secondary"]) button:hover {
            background-color: #ff4b4b !important;
            color: white !important;
            border-color: #ff4b4b !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2.8, 0.5, 0.3])
    
    with col3:
        if st.button("Logout", key="logout_btn", use_container_width=True):
            logout()
    
    with col2:
        st.markdown(f"<div style='text-align: right; margin-top: 8px; font-size: 12px;'>{st.session_state.username}</div>", unsafe_allow_html=True)

# --------- -----------------------------------------------
# CUSTOM CSS - LOAD FROM EXTERNAL FILE
# --------- -----------------------------------------------
css_path = project_root / "app/assets/sidebar_styles.css"
if css_path.exists():
    with open(css_path, 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    logger.warning(f"CSS file not found: {css_path}")

# -----------------------------------------------------
# SIDEBAR LOGO
# -----------------------------------------------------
try:
    logo_path = (project_root / "app/assets/logo.jpeg").resolve()
    logger.info(f"Logo path resolved: {logo_path}")

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
# Icon mapping for each page (Option B — Action-Oriented)
page_icons = {
    "Upload & Ingest": "📁",
    "Audit Bills": "📄",
    "Manage Tariffs": "📑",
    "Pipeline Status": "📊",
    "Generate Reports": "📋",
    "Upload History": "📜",
}

# Add custom HTML for tooltip support
st.sidebar.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const labels = {
        '📁': 'Upload & Ingest',
        '📄': 'Audit Bills',
        '▶️': 'Execute Pipeline',
        '📊': 'Pipeline Status',
        '📋': 'Generate Reports',
        '📑': 'Manage Tariffs',
        '📜': 'Upload History'
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

# Create navigation with icon labels
page_options = list(page_icons.keys())

# Initialize nav_state in session state if not present
if "nav_state" not in st.session_state:
    st.session_state.nav_state = "home"

# Check if on home
show_home = st.session_state.nav_state == "home"

# Show sidebar navigation only if not on home
if not show_home:
    # Navigation section
    st.sidebar.markdown("### 📍 Navigation")
    default_index = page_options.index(st.session_state.nav_state) if st.session_state.nav_state in page_options else 0
    selected_page = st.sidebar.radio(
        "Pages",
        page_options,
        index=default_index,
        format_func=lambda x: f"{page_icons[x]}  {x}",
        label_visibility="collapsed"
    )
    # Keep nav_state in sync with sidebar selection
    if selected_page != st.session_state.nav_state:
        st.session_state.nav_state = selected_page
    
    st.sidebar.markdown("---")
    
    # Back to Home button
    if st.sidebar.button("🏠 Back to Home", use_container_width=True):
        st.session_state.nav_state = "home"
        st.rerun()
    
    page = selected_page
else:
    page = None

# Show dashboard if on home page
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
    <div style="display: flex; align-items: center; justify-content: center; height: 500px; flex-direction: column; gap: 20px;">
        <div style="font-size: 120px; text-align: center;">🚀</div>
        <div style="text-align: center;">
            <h1 style="font-size: 48px; font-weight: 800; margin: 0;">Coming Soon</h1>
            <p style="font-size: 18px; opacity: 0.8; margin-top: 10px; color: #666;">Pipeline Status monitoring feature is under development.</p>
            <p style="font-size: 14px; opacity: 0.6; color: #999;">Check back soon for real-time pipeline execution tracking and logs.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

elif page == "Generate Reports":
    from app.components.reports_viewer import render_report_viewer
    render_report_viewer()

elif page == "Upload History":
    from app.components.upload_history import render_upload_history
    render_upload_history()

# -----------------------------------------------------
# FOOTER
# -----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.caption("© 2025 Troy & Banks | Utility Billing AI Prototype")
