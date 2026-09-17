from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemplateScope(str, Enum):
    common = "common"
    private = "private"


class TemplateStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class TemplateReferenceInput(BaseModel):
    storage_key: str
    label: str | None = None


class TemplateReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    storage_key: str
    label: str | None = None


class ImageTemplateCreateRequest(BaseModel):
    scope: TemplateScope
    wholesaler_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    model: str | None = None
    background: str | None = None
    colors: dict | None = None
    rack: str | None = None
    prompt: str | None = None
    references: list[TemplateReferenceInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scope(self) -> "ImageTemplateCreateRequest":
        if self.scope == TemplateScope.private and not self.wholesaler_id:
            raise ValueError("private templates require wholesaler_id")
        if self.scope == TemplateScope.common and self.wholesaler_id:
            raise ValueError("common templates must not set wholesaler_id")
        return self


class ImageTemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    model: str | None = None
    background: str | None = None
    colors: dict | None = None
    rack: str | None = None
    prompt: str | None = None
    references: list[TemplateReferenceInput] | None = None


class ImageTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: TemplateScope
    wholesaler_id: UUID | None
    version: int
    status: TemplateStatus
    name: str
    model: str | None
    background: str | None
    colors: dict | None
    rack: str | None
    prompt: str | None
    references: list[TemplateReferenceResponse]
    created_at: datetime
    updated_at: datetime
