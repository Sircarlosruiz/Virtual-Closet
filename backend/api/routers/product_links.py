"""Cookie-authenticated lookup of explicit product links for staff UI."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.product_link import ProductLinkLookupResponse
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.product_link_repo import ProductLinkRepository
from services.product_link_service import (
    ProductLinkMismatchError,
    ProductLinkNotFoundError,
    ProductLinkService,
)

router = APIRouter(prefix="/api/product-links", tags=["product-links"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )
    if mayorista.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff actor does not belong to this tenant",
        )


@router.get("/lookup", response_model=ProductLinkLookupResponse)
async def lookup_product_link(
    external_product_id: str = Query(..., min_length=1, max_length=255),
    system: str = Query("bfashion", min_length=1, max_length=40),
    external_wholesaler_id: str | None = Query(None, max_length=255),
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> ProductLinkLookupResponse:
    """Resolve an explicit product link from external ids. Fail closed."""
    _require_staff(mayorista)
    tenant_id = mayorista.tenant_id
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff actor does not belong to this tenant",
        )
    service = ProductLinkService(ProductLinkRepository(db))
    try:
        link = await service.resolve_active_link(
            system,
            external_product_id,
            external_wholesaler_id,
            tenant_id,
        )
    except ProductLinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ProductLinkMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return ProductLinkLookupResponse.model_validate(link)
