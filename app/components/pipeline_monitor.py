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


def poll_job_status(job_id: str, poll_interval: float = 3.0):
    """Poll status and update progress bar. Stops if job is superseded."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    while True:
        # If a newer job was registered, stop polling this one
        if st.session_state.get("current_job_id") != job_id:
            status_text.info("A newer job has taken over — stopping poll.")
            return

        res = requests.get(f"{API_BASE_URL}/api/v1/processing/tariffs/status/{job_id}")
        if not res.ok:
            status_text.error("Could not reach status endpoint.")
            return

        data = res.json()
        step        = data.get("step", 0)
        total_steps = data.get("total_steps", 3)
        message     = data.get("message", "")
        status      = data.get("status", "running")

        progress_bar.progress(step / total_steps)
        status_text.write(f"Step {step}/{total_steps}: {message}")

        if status == "completed":
            status_text.success("✅ Processing complete!")
            return
        if status == "cancelled":
            status_text.warning("⚠️ Job was superseded by a newer request.")
            return
        if status == "failed":
            status_text.error(f"❌ Failed: {message}")
            return

        time.sleep(poll_interval)