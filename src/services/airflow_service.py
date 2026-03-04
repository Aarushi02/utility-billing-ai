import time
from datetime import datetime, timezone

import requests

from src.utils.config import (
    AIRFLOW_API_PASSWORD,
    AIRFLOW_API_URL,
    AIRFLOW_API_USER,
    AIRFLOW_DAG_ID,
)


class AirflowService:
    _cached_token: str | None = None
    _token_expires_at: float = 0.0

    def _get_jwt_token(self) -> str:
        base_url = AIRFLOW_API_URL.replace("/api/v2", "")
        auth_url = f"{base_url}/auth/token"

        response = requests.post(
            auth_url,
            json={
                "username": AIRFLOW_API_USER,
                "password": AIRFLOW_API_PASSWORD,
            },
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        response.raise_for_status()

        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("No access_token in Airflow auth response")
        return token

    def _get_jwt_token_cached(self) -> str:
        current_time = time.time()
        if self._cached_token and current_time < (self._token_expires_at - 30):
            return self._cached_token

        token = self._get_jwt_token()
        self._cached_token = token
        self._token_expires_at = current_time + 3600
        return token

    def trigger_dag_run(self) -> str:
        token = self._get_jwt_token_cached()
        url = f"{AIRFLOW_API_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns"

        payload = {
            "dag_run_id": f"manual__{int(time.time())}",
            "logical_date": datetime.now(timezone.utc).isoformat(),
            "conf": {},
        }

        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )
        response.raise_for_status()

        body = response.json()
        dag_run_id = body.get("dag_run_id") or body.get("run_id")
        if not dag_run_id:
            raise RuntimeError("Airflow trigger response missing dag_run_id")
        return dag_run_id

    def get_dag_run_state(self, dag_run_id: str) -> str:
        token = self._get_jwt_token_cached()
        url = f"{AIRFLOW_API_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns/{dag_run_id}"

        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("state", "unknown")

    def get_task_statuses(self, dag_run_id: str) -> list[dict]:
        token = self._get_jwt_token_cached()
        url = f"{AIRFLOW_API_URL}/dags/{AIRFLOW_DAG_ID}/dagRuns/{dag_run_id}/taskInstances"

        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        response.raise_for_status()

        tasks = response.json().get("task_instances", [])
        return [
            {
                "task_id": str(task.get("task_id", "unknown")),
                "state": task.get("state"),
            }
            for task in tasks
        ]

    def get_run_status(self, dag_run_id: str) -> dict:
        state = self.get_dag_run_state(dag_run_id)
        tasks = self.get_task_statuses(dag_run_id)
        return {
            "dag_run_id": dag_run_id,
            "state": state,
            "tasks": tasks,
            "raw": None,
        }
