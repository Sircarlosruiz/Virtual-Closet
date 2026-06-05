import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BatchItemStatus(str):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class BatchJobStatus(str):
    pending = "pending"
    in_progress = "in-progress"
    complete = "complete"
    partial = "partial"
    failed = "failed"


class BatchItemCreateRequest(BaseModel):
    garment_id: uuid.UUID
    model_id: uuid.UUID
    cloth_type: str

    @field_validator("cloth_type")
    @classmethod
    def validate_cloth_type(cls, v: str) -> str:
        allowed = {"upper_body", "lower_body", "dress"}
        if v not in allowed:
            raise ValueError(
                f"cloth_type must be one of: {', '.join(sorted(allowed))}"
            )
        return v


class BatchCreateRequest(BaseModel):
    name: str | None = None
    items: list[BatchItemCreateRequest]

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[BatchItemCreateRequest]) -> list[BatchItemCreateRequest]:
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 item")
        if len(v) > 100:
            raise ValueError("Batch size exceeds maximum of 100 items")
        return v


class BatchItemResponse(BaseModel):
    id: uuid.UUID
    garment_id: uuid.UUID
    model_id: uuid.UUID
    cloth_type: str
    status: str
    vton_job_id: uuid.UUID | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime


class BatchCreateResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    total_items: int
    completed_count: int = 0
    failed_count: int = 0
    created_at: datetime


class BatchDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    total_items: int
    completed_count: int
    failed_count: int
    created_at: datetime
    completed_at: datetime | None = None
    items: list[BatchItemResponse]


class BatchListItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    total_items: int
    completed_count: int
    failed_count: int
    created_at: datetime


class BatchListResponse(BaseModel):
    items: list[BatchListItemResponse]
    total: int
    page: int
    page_size: int
