import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MagicLinkRequest(BaseModel):
    email: EmailStr


class PortalAuthResponse(BaseModel):
    message: str
    customer_id: uuid.UUID
    mayorista_id: uuid.UUID


class PortalCatalogResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    item_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortalCatalogListResponse(BaseModel):
    catalogs: list[PortalCatalogResponse]
    total: int
    page: int
    page_size: int


class PortalCatalogItemResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    garment_name: str
    price: Decimal
    cloth_type: str
    sku: str
    position: int


class PortalCatalogDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    item_count: int
    created_at: datetime
    items: list[PortalCatalogItemResponse]
