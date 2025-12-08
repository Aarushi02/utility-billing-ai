"""
home.py
-------
Home/authentication logic module.
"""

import streamlit as st


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


