from typing import Any

from pydantic import BaseModel


class AirflowTriggerResponse(BaseModel):
    dag_run_id: str


class AirflowTaskStatus(BaseModel):
    task_id: str
    state: str | None = None


class AirflowRunStatusResponse(BaseModel):
    dag_run_id: str
    state: str
    tasks: list[AirflowTaskStatus]
    raw: dict[str, Any] | None = None
