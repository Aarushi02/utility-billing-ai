from fastapi import APIRouter, HTTPException

from src.api.schemas.jobs import JobCreateRequest, JobCreateResponse, JobStatusResponse
from src.services.workflow_service import WorkflowService


router = APIRouter(prefix="/jobs")
service = WorkflowService()


@router.post("", response_model=JobCreateResponse)
def submit_job(payload: JobCreateRequest) -> JobCreateResponse:
    job = service.submit_job(job_type=payload.job_type)
    return JobCreateResponse(job_id=job["job_id"], status=job["status"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = service.get_job_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JobStatusResponse(**job)
