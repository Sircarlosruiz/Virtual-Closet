"""API contract for the authenticated Virtual Closet <-> BFashion bridge."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.image_generation import (
    GenerationMode,
    GenerationProvider,
    ImageGenerationRequest,
)


class ProductGenerationBridgeRequest(BaseModel):
    """Server-to-server command to generate imagery for a linked product.

    ``staff_id`` is asserted by the calling application but is re-validated
    against Virtual Closet's own records before any job is created.
    """

    staff_id: UUID
    external_product_id: str = Field(min_length=1, max_length=255)
    external_wholesaler_id: str | None = Field(default=None, max_length=255)
    generation: ImageGenerationRequest


class ProductGenerationBridgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    external_product_id: str
    mode: GenerationMode
    provider: GenerationProvider
    status: str
    created_at: datetime


class ProductGenerationBridgeStatusResponse(ProductGenerationBridgeResponse):
    updated_at: datetime
    preview_url: str | None = None


class ProductPublicationBridgeRequest(BaseModel):
    """Server-to-server command to select or discard a generation result."""

    staff_id: UUID
    generation_job_id: UUID
    composition_version_id: UUID | None = None
    decision: Literal["selected", "discarded"]
    external_wholesaler_id: str | None = Field(default=None, max_length=255)
