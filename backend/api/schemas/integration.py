"""API contract for the authenticated Virtual Closet <-> BFashion bridge."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

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


SourceImageKind = Literal["garment_on_model", "flat_garment"]
SourceImageContentType = Literal["image/jpeg", "image/png"]


class SourceImagePresignRequest(BaseModel):
    """Request a short-lived PUT grant. ``system`` / ``tenant_id`` are ignored."""

    model_config = ConfigDict(extra="ignore")

    staff_id: UUID
    kind: SourceImageKind
    content_type: SourceImageContentType
    size_bytes: int = Field(gt=0)
    filename: str = Field(min_length=1, max_length=255)
    external_wholesaler_id: str | None = Field(default=None, max_length=255)


class SourceImagePresignResponse(BaseModel):
    source_image_id: UUID
    upload_url: str
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str]
    expires_in: int
    storage_key: str


class SourceImageConfirmRequest(BaseModel):
    """Confirm a direct upload. ``system`` / ``tenant_id`` are ignored."""

    model_config = ConfigDict(extra="ignore")

    staff_id: UUID
    checksum_sha256: str | None = Field(default=None, max_length=64)
    external_wholesaler_id: str | None = Field(default=None, max_length=255)


class SourceImageConfirmResponse(BaseModel):
    source_image_id: UUID
    kind: SourceImageKind
    status: Literal["ready"]
    content_type: str
    size_bytes: int
    preview_url: str | None = None


class PhotoshootCatalogTemplate(BaseModel):
    id: UUID
    name: str
    scope: Literal["common", "private"]
    wholesaler_scope: UUID | None
    version: int
    model: str | None
    background: str | None
    colors: Any | None = None
    rack: str | None
    updated_at: datetime


class PhotoshootCatalogModel(BaseModel):
    id: UUID
    name: str
    available_poses: list[Literal["front", "side", "back"]]
    preview_url: str | None = None


class PhotoshootClothTypeOption(BaseModel):
    value: Literal["upper_body", "lower_body", "dress"]
    label: str


class PhotoshootOptionsResponse(BaseModel):
    templates: list[PhotoshootCatalogTemplate]
    models: list[PhotoshootCatalogModel]
    cloth_types: list[PhotoshootClothTypeOption]
    background_suggestions: list[str]
    color_suggestions: list[str]
    max_pose_count: int
    catalog_version: str


PoseType = Literal["front", "side", "back"]
PhotoshootInputKind = Literal["garment_on_model", "flat_garment"]
PhotoshootClothType = Literal["upper_body", "lower_body", "dress"]


class PhotoshootOverlayRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = ""
    placement: Any | None = None
    style: Any | None = None


class PhotoshootCreateRequest(BaseModel):
    """Server-to-server command to start a high-level photoshoot (FR-5)."""

    model_config = ConfigDict(extra="ignore")

    staff_id: UUID
    external_wholesaler_id: str | None = Field(default=None, max_length=255)
    source_image_id: UUID
    input_kind: PhotoshootInputKind
    template_id: UUID | None = None
    model_ids: list[UUID] = Field(min_length=1)
    pose_ids: list[PoseType] | None = None
    pose_count: int | None = Field(default=None, ge=1, le=3)
    cloth_type: PhotoshootClothType
    background: str | None = None
    colors: Any | None = None
    overlay: PhotoshootOverlayRequest | None = None
    variant_key: str | None = None

    @model_validator(mode="after")
    def pose_ids_xor_pose_count(self) -> "PhotoshootCreateRequest":
        if self.pose_ids is not None and self.pose_count is not None:
            raise ValueError("pose_ids and pose_count are mutually exclusive")
        return self


class PhotoshootStageResponse(BaseModel):
    name: str
    status: str


class PhotoshootCreateResponse(BaseModel):
    photoshoot_id: UUID
    external_product_id: str
    status: str
    expected_results: int
    stages: list[PhotoshootStageResponse]
    created_at: datetime
