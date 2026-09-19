"""API contract for the authenticated Virtual Closet <-> BFashion bridge."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.schemas.image_generation import (
    GenerationMode,
    GenerationProvider,
    ImageGenerationRequest,
)

StaffRole = Literal["admin", "owner", "staff"]


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


class ProductLinkCreateRequest(BaseModel):
    """Create the explicit product link. ``system`` / ``tenant_id`` are ignored."""

    model_config = ConfigDict(extra="ignore")

    external_product_id: str = Field(min_length=1, max_length=255)
    staff_id: UUID
    external_wholesaler_id: str | None = Field(default=None, max_length=255)
    prenda_id: UUID | None = None


class ProductLinkCreateResponse(BaseModel):
    product_link_id: UUID
    external_product_id: str
    mayorista_id: UUID
    tenant_id: UUID
    is_active: bool
    created: bool


class StaffIdentityProvisionRequest(BaseModel):
    """Provision a Mayorista mirror. ``system`` / ``tenant_id`` are ignored."""

    model_config = ConfigDict(extra="ignore")

    external_staff_id: str = Field(min_length=1, max_length=255)
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    role: StaffRole = "staff"


class StaffIdentityProvisionResponse(BaseModel):
    staff_id: UUID
    external_staff_id: str
    email: str
    role: str
    is_active: bool
    created: bool


class StaffIdentityRevokeResponse(BaseModel):
    staff_id: UUID
    external_staff_id: str
    is_active: bool
