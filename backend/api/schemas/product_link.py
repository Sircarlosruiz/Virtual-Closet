"""Cookie-staff DTOs for explicit product-link lookup."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductLinkLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system: str
    external_product_id: str
    external_wholesaler_id: str | None
    is_active: bool
