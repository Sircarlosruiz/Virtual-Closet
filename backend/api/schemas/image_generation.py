from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerationMode(str, Enum):
    try_on = "try_on"
    text = "text"
    edit = "edit"
    extraction = "extraction"


class GenerationProvider(str, Enum):
    openai = "openai"
    vton = "vton"


class ImageGenerationRequest(BaseModel):
    mode: GenerationMode
    provider: GenerationProvider | None = None
    prompt: str | None = None
    garment_id: UUID | None = None
    model_id: UUID | None = None
    cloth_type: str | None = None
    reference_image_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_inputs(self) -> "ImageGenerationRequest":
        provider = self.provider or GenerationProvider.openai
        prompt = self.prompt.strip() if self.prompt else ""
        if self.mode == GenerationMode.try_on:
            if not self.garment_id or not self.model_id or not self.cloth_type:
                raise ValueError("try_on requires garment_id, model_id and cloth_type")
            if provider not in {GenerationProvider.openai, GenerationProvider.vton}:
                raise ValueError("try_on provider is unsupported")
        elif provider != GenerationProvider.openai:
            raise ValueError("only openai supports this generation mode")

        if self.mode == GenerationMode.text and not prompt:
            raise ValueError("text requires a non-empty prompt")
        if self.mode == GenerationMode.edit:
            if not prompt:
                raise ValueError("edit requires a non-empty prompt")
            if not self.reference_image_ids:
                raise ValueError("edit requires at least one reference image")
        if self.mode == GenerationMode.extraction and not self.reference_image_ids:
            raise ValueError("extraction requires at least one reference image")
        return self


class ImageGenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    mode: GenerationMode
    provider: GenerationProvider
    status: str
    created_at: datetime


class ProviderAttemptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attempt_number: int
    status: str
    error_code: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class UsageSummary(BaseModel):
    status: str
    model: str | None = None
    call_count: int | None = None


class ImageGenerationDetailResponse(ImageGenerationResponse):
    attempts: list[ProviderAttemptSummary] = Field(default_factory=list)
    usage: UsageSummary
    preview_url: str | None = None
