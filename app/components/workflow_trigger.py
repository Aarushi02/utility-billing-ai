"""Streamlit component for submitting and monitoring workflow jobs via API."""

import time

import requests
import streamlit as st

from src.utils.config import get_env


API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


def _get_api_json(path: str):
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
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


def _post_api_json(path: str, payload: dict):
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
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


# -------------------------------------------------------------------
# Public entry point
# -------------------------------------------------------------------
def render_workflow_trigger():
    """Renders the Streamlit UI section to trigger and monitor workflow jobs."""
    st.title("Run Workflow")
    st.caption("Submit workflow as a background API job and monitor status.")

    if "workflow_job_id" not in st.session_state:
        st.session_state.workflow_job_id = None

    if st.button("Start Workflow"):
        try:
            job = _post_api_json("/api/v1/jobs", {"job_type": "full_workflow"})
            st.session_state.workflow_job_id = job.get("job_id")
            st.success(f"Workflow job submitted: {st.session_state.workflow_job_id}")
        except requests.RequestException as exc:
            st.error(f"Unable to submit workflow job: {exc}")
            return

    job_id = st.session_state.workflow_job_id
    if not job_id:
        st.info("No active workflow job. Click 'Start Workflow' to submit one.")
        return

    try:
        job = _get_api_json(f"/api/v1/jobs/{job_id}")
    except requests.RequestException as exc:
        st.error(f"Unable to fetch workflow status: {exc}")
        return

    status = str(job.get("status", "unknown")).lower()
    st.write(f"Job ID: {job_id}")
    st.write(f"Status: {status}")

    if status in {"queued", "running"}:
        st.info("Workflow is still running. Auto-refreshing...")
        time.sleep(2)
        st.rerun()
        return

    if status == "completed":
        st.success("Workflow completed successfully.")
    else:
        st.error(f"Workflow failed: {job.get('error') or 'Unknown error'}")

    if st.button("Clear Job Status"):
        st.session_state.workflow_job_id = None
        st.rerun()


if __name__ == "__main__":
    # For standalone local test
    render_workflow_trigger()
