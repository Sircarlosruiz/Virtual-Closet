from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ModeloIAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    descripcion: str | None = None
    thumbnail_url: str
    plan_minimo: str
