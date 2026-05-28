import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CatalogStatus(str, Enum):
    draft = "draft"
    published = "published"


class ClothType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dress = "dress"


class CatalogoCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Catalog name cannot be empty or whitespace only")
        return stripped


class CatalogoResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: CatalogStatus
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CatalogoUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    status: CatalogStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Catalog name cannot be empty or whitespace only")
        return stripped


class CatalogoListResponse(BaseModel):
    catalogs: list[CatalogoResponse]
    total: int
    page: int
    page_size: int


class CatalogoItemAddRequest(BaseModel):
    vton_job_id: uuid.UUID | None = None
    generacion_id: uuid.UUID | None = None
    garment_name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    cloth_type: ClothType
    sku: str = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_source(self) -> "CatalogoItemAddRequest":
        has_vton = self.vton_job_id is not None
        has_generacion = self.generacion_id is not None
        if has_vton == has_generacion:
            raise ValueError(
                "Provide exactly one of vton_job_id or generacion_id"
            )
        return self


class CatalogoItemResponse(BaseModel):
    id: uuid.UUID
    catalog_id: uuid.UUID
    vton_job_id: uuid.UUID | None = None
    generacion_id: uuid.UUID | None = None
    image_url: str
    garment_name: str
    price: Decimal
    cloth_type: ClothType
    sku: str
    position: int
    created_at: datetime


class CatalogoReorderRequest(BaseModel):
    ordered_item_ids: list[uuid.UUID] = Field(..., min_length=1)


class CatalogoReorderItemResponse(BaseModel):
    id: uuid.UUID
    position: int
    garment_name: str
    image_url: str
    price: Decimal
    cloth_type: ClothType
    sku: str


class CatalogoReorderResponse(BaseModel):
    items: list[CatalogoReorderItemResponse]


class CatalogoDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: CatalogStatus
    item_count: int
    created_at: datetime
    updated_at: datetime
    items: list[CatalogoItemResponse]
