from datetime import datetime

from pydantic import BaseModel


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
