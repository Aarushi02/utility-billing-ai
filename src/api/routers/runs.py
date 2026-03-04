from fastapi import APIRouter

from src.api.schemas.runs import PipelineRunsResponse
from src.services.workflow_service import WorkflowService


router = APIRouter(prefix="/runs")
service = WorkflowService()


@router.get("", response_model=PipelineRunsResponse)
def list_runs(limit: int = 20) -> PipelineRunsResponse:
    return PipelineRunsResponse(runs=service.get_recent_runs(limit=limit))
