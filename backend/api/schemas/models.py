import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mayorista_id: uuid.UUID
    name: str
    created_at: datetime


class ModelListItemResponse(ModelResponse):
    pose_count: int


class ModelListResponse(BaseModel):
    items: list[ModelListItemResponse]
    total: int


class PosePhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_id: uuid.UUID
    pose: str
    presigned_url: str
    uploaded_at: datetime


class PoseListResponse(BaseModel):
    items: list[PosePhotoResponse]
    total: int
