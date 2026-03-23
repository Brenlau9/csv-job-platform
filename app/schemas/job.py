from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    file_id: int
    job_type: str


class JobResponse(BaseModel):
    id: int
    user_id: int
    file_id: int
    job_type: str
    status: str
    attempt_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: int
    job_type: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SummaryResultPayload(BaseModel):
    row_count: int
    column_count: int
    columns: list[str]
    null_counts: dict[str, int]


class JobResultResponse(BaseModel):
    job_id: int
    result: SummaryResultPayload


class JobListResponse(BaseModel):
    items: list[JobStatusResponse]
    page: int
    page_size: int
    total: int
