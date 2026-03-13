"""Utility functions to trigger and monitor Airflow through backend API endpoints."""

import time
from typing import Any

import requests
import streamlit as st

from src.utils.config import get_env
from src.utils.logger import get_logger


logger = get_logger(__name__)
API_BASE_URL = get_env("API_BASE_URL", "http://localhost:8000")


def _post_api_json(path: str, payload: dict | None = None) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.post(f"{API_BASE_URL}{path}", json=payload or {}, timeout=30)
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

    raise RuntimeError("Unexpected API POST flow: no response and no exception captured")


def _get_api_json(path: str) -> dict[str, Any]:
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

    raise RuntimeError("Unexpected API GET flow: no response and no exception captured")


def trigger_dag_run():
    """Trigger DAG run via backend API and return dag_run_id or None."""
    try:
        body = _post_api_json("/api/v1/airflow/dag-runs")
        dag_run_id = body.get("dag_run_id")
        if dag_run_id:
            logger.info("Successfully triggered DAG run via backend API: %s", dag_run_id)
            st.success(f"✅ Triggered Airflow DAG Run: {dag_run_id}")
            return dag_run_id
        st.error("❌ Trigger response did not include dag_run_id")
        return None
    except requests.RequestException as exc:
        logger.error("Failed to trigger DAG via backend API: %s", exc)
        st.error(f"❌ Failed to trigger DAG: {exc}")
        return None


def monitor_dag_run(dag_run_id: str, refresh_interval: int = 5):
    """Poll backend API for DAG/task status and render in Streamlit."""
    progress_placeholder = st.empty()
    state = "running"

    while state in {"queued", "running"}:
        try:
            status_body = _get_api_json(f"/api/v1/airflow/dag-runs/{dag_run_id}")
        except requests.RequestException as exc:
            logger.error("Failed to fetch DAG status via backend API: %s", exc)
            st.error(f"❌ Could not fetch DAG status: {exc}")
            return

        state = str(status_body.get("state", "unknown"))
        tasks = status_body.get("tasks", [])

        with progress_placeholder.container():
            st.subheader(f"📊 DAG Status: **{state.upper()}**")
            st.write("**Task Progress:**")

            if tasks:
                for task in tasks:
                    task_id = task.get("task_id", "unknown")
                    task_state = task.get("state", "unknown")
                    if task_state == "success":
                        st.write(f"✅ {task_id}: {task_state}")
                    elif task_state == "failed":
                        st.write(f"❌ {task_id}: {task_state}")
                    elif task_state == "running":
                        st.write(f"⏳ {task_id}: {task_state}")
                    else:
                        st.write(f"• {task_id}: {task_state}")
            else:
                st.write("No tasks found yet...")

        if state in {"success", "failed"}:
            break
        time.sleep(refresh_interval)

    if state == "success":
        st.success("✅ Workflow completed successfully!")
    elif state == "failed":
        st.error("❌ Workflow failed — check Airflow logs for details.")
