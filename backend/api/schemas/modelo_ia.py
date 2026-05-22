from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ModeloIACreateRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=500)
    modelo_id: UUID
    object_key: str


class ModeloIAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    descripcion: str | None = None
    thumbnail_url: str
    plan_minimo: str
