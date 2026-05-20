from uuid import UUID
from pydantic import BaseModel, ConfigDict


class GeneracionCreate(BaseModel):
    prenda_id: UUID
    modelo_ia_id: UUID


class GeneracionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prenda_id: UUID
    modelo_ia_id: UUID
    estado: str
    imagen_url: str | None = None
    thumbnail_url: str | None = None
    costo_inferencia_usd: float | None = None
    error_message: str | None = None
    created_at: str
