import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ClothType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dress = "dress"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VTONGenerateRequest(BaseModel):
    garment_photo_id: uuid.UUID
    model_photo_id: uuid.UUID
    cloth_type: ClothType


class VTONJobCreateResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    created_at: datetime


class VTONJobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_url: str | None = None
    error_reason: str | None = None
    retry_count: int = 0
