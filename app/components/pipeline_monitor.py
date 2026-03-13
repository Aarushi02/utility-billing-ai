import streamlit as st
import pandas as pd
import requests
import time

from src.utils.config import get_env


API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


@st.cache_data(ttl=30, show_spinner=False)
def _get_api_json(path: str, params: dict | None = None):
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise

    if last_exc:
        raise last_exc

def render_pipeline_monitor():
    st.title("Pipeline Monitor")

    try:
        runs = _get_api_json("/api/v1/runs", params={"limit": 20}).get("runs", [])
    except requests.RequestException as exc:
        st.error(f"Unable to load pipeline runs from API: {exc}")
        return

    df = pd.DataFrame(runs)

    if df.empty:
        st.info("No pipeline runs logged.")
    else:
        st.dataframe(df, use_container_width=True)
