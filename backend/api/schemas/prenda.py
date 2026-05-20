from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadUrlRequest(BaseModel):
    extension: Literal["jpg", "png", "heic"]


class UploadUrlResponse(BaseModel):
    upload_url: str
    prenda_id: UUID
    object_key: str


class ConfirmarSubidaRequest(BaseModel):
    prenda_id: UUID
    object_key: str
    nombre: str | None = None


class PrendaResponse(BaseModel):
    id: UUID
    nombre: str
    imagen_original_url: str
    estado: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActualizarNombreRequest(BaseModel):
    nombre: str = Field(..., max_length=80, min_length=1)


class PrendasListResponse(BaseModel):
    items: list[PrendaResponse]
    next_cursor: UUID | None
