"""Tenant management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.tenant import TenantResponse, TenantUpdateRequest
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.tenant_repo import TenantRepo
from services.tenant_service import (
    TenantInactiveError,
    TenantNotFoundError,
    TenantService,
    TenantSlugConflictError,
)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


def _get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    tenant_repo = TenantRepo(db)
    return TenantService(tenant_repo)


@router.get("/me", response_model=TenantResponse)
async def get_tenant(
    mayorista: Mayorista = Depends(get_current_mayorista),
    tenant_service: TenantService = Depends(_get_tenant_service),
):
    """Get the current mayorista's tenant."""
    try:
        tenant = await tenant_service.get_tenant(mayorista.tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return tenant


@router.patch("/me", response_model=TenantResponse)
async def update_tenant(
    body: TenantUpdateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    tenant_service: TenantService = Depends(_get_tenant_service),
):
    """Update the current mayorista's tenant name and/or settings."""
    try:
        tenant = await tenant_service.update_tenant(
            tenant_id=mayorista.tenant_id,
            name=body.name,
            settings=body.settings,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantSlugConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return tenant
