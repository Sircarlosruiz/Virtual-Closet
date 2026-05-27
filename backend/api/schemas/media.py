import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class GarmentPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    presigned_url: str
    filename: str
    uploaded_at: datetime


class ModelPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    presigned_url: str
    label: str
    is_curated: bool
    uploaded_at: datetime


class PaginatedGarmentPhotos(BaseModel):
    items: list[GarmentPhotoResponse]
    total: int
    page: int
    page_size: int


class PaginatedModelPhotos(BaseModel):
    items: list[ModelPhotoResponse]
    total: int
    page: int
    page_size: int
