"""Pydantic schemas for tenant, admin invitation, and buyer link APIs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Tenant Schemas ---

class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    settings: dict | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Tenant name cannot be empty or whitespace only")
        return stripped


# --- Admin Invitation Schemas ---

class AdminInvitationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    expires_at: datetime
    accepted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminInviteRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        stripped = v.strip()
        if "@" not in stripped:
            raise ValueError("Invalid email address")
        return stripped


class AdminListResponse(BaseModel):
    invitations: list[AdminInvitationResponse]


class AcceptInvitationRequest(BaseModel):
    token: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


# --- Buyer Link Schemas ---

class BuyerLinkRequest(BaseModel):
    catalog_ids: list[uuid.UUID] = Field(..., min_length=1)
    ttl_days: int = Field(30, ge=1, le=365)


class BuyerLinkResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    catalog_ids: list[uuid.UUID]
    signed_url: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidateLinkRequest(BaseModel):
    token: str = Field(..., min_length=1)


class ValidateLinkResponse(BaseModel):
    valid: bool
    tenant_id: uuid.UUID | None = None
    catalog_ids: list[uuid.UUID] | None = None
    error: str | None = None


class BuyerLinkListResponse(BaseModel):
    links: list[BuyerLinkResponse]
