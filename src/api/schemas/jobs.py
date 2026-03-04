from datetime import datetime

from pydantic import BaseModel


class JobCreateRequest(BaseModel):
    job_type: str = "full_workflow"


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: bool | None = None
    error: str | None = None
