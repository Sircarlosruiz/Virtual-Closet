import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class GarmentType(str, Enum):
    upper = "upper"
    lower = "lower"
    dress = "dress"


class TryoffJobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class TryoffJobRequest(BaseModel):
    source_image_id: uuid.UUID
    garment_type: GarmentType


class TryoffBatchRequest(BaseModel):
    source_image_id: uuid.UUID
    garment_types: list[GarmentType] = Field(..., min_length=1)


class TryoffJobResponse(BaseModel):
    job_id: uuid.UUID
    status: TryoffJobStatus
    garment_type: GarmentType
    created_at: datetime


class TryoffBatchResponse(BaseModel):
    jobs: list[TryoffJobResponse]


class TryoffJobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: TryoffJobStatus
    garment_type: GarmentType
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_url: str | None = None
    error_reason: str | None = None
    retry_count: int = 0


class TryoffJobHistoryItem(BaseModel):
    job_id: uuid.UUID
    status: TryoffJobStatus
    garment_type: GarmentType
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_url: str | None = None
    error_reason: str | None = None
    retry_count: int = 0


class TryoffJobHistoryResponse(BaseModel):
    items: list[TryoffJobHistoryItem]
    total: int
    page: int
    page_size: int
