from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel

from src.services.workflow_service import WorkflowService


class PipelineRunItem(BaseModel):
    id: int
    dag_id: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: str | None = None
    total_runtime: int | None = None
    error_msg: str | None = None
    created_at: datetime | None = None


class PipelineRunsResponse(BaseModel):
    runs: list[PipelineRunItem]


router = APIRouter(prefix="/runs")
service = WorkflowService()


@router.get("", response_model=PipelineRunsResponse)
def list_runs(limit: int = 20) -> PipelineRunsResponse:
    return PipelineRunsResponse(runs=service.get_recent_runs(limit=limit))
