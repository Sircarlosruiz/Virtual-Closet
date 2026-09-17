from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EffectiveConfiguration(BaseModel):
    model: str | None = None
    background: str | None = None
    colors: dict | None = None
    rack: str | None = None
    prompt: str | None = None
    provider: str
    reference_keys: list[str]
    template_version: int


class CompositionSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generation_job_id: UUID
    template_id: UUID
    template_version: int
    effective_configuration: EffectiveConfiguration
    created_at: datetime


class RegenerateResponse(BaseModel):
    job_id: UUID
    status: str
