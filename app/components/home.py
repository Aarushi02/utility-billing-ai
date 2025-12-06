import streamlit as st
from src.utils.config import get_env


def render_login_page():
    """Login page - authentication gate for the entire application."""
    
    # Custom CSS for login page
    st.markdown("""
        <style>
        .login-container {
            max-width: 450px;
            margin: 100px auto;
            padding: 40px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .login-title {
            text-align: center;
            color: #1f4788;
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .login-subtitle {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-title">🔐 Utility Billing AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Login to access the system</div>', unsafe_allow_html=True)
        
        # Pull expected credentials from env/secrets
        expected_user = get_env("LOGIC_USERNAME")
        expected_pass = get_env("LOGIC_PASSWORD")

        if not expected_user or not expected_pass:
            st.error("⚠️ Login credentials are not configured. Set LOGIC_USERNAME and LOGIC_PASSWORD in .env or secrets.")
            return

        # Login form
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if username == expected_user and password == expected_pass:
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                
        st.markdown("---")
        st.caption("© 2025 Troy & Banks | Utility Billing AI")


def check_authentication():
    """Check if user is authenticated. Returns True if authenticated, False otherwise."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    return st.session_state.authenticated


def logout():
    """Logout user and clear session state."""
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.authenticated = False
    st.rerun()
