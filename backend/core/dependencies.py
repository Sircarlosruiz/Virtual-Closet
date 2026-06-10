from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from models.mayorista import Mayorista
from models.tenant import Tenant
from services.token_service import TokenService
from repositories.customer_repo import CustomerRepo
from repositories.tenant_repo import TenantRepo
from dataclasses import dataclass
from uuid import UUID


async def get_current_mayorista(
    access_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Mayorista:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    mayorista_id = payload.get("sub")
    if not mayorista_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(Mayorista).where(Mayorista.id == UUID(mayorista_id)))
    mayorista = result.scalar_one_or_none()
    if not mayorista:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return mayorista


async def get_current_buyer(
    buyer_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate buyer session cookie."""
    from models.customer import Customer

    if not buyer_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token_service = TokenService()
    payload = token_service.decode_token(buyer_session)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    if payload.get("type") != "buyer_session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session type",
        )

    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session payload",
        )

    customer_repo = CustomerRepo(db)
    customer = await customer_repo.get_by_id(UUID(customer_id))

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found",
        )

    return customer


@dataclass
class TenantContext:
    """Context object injected into routes that require tenant scoping."""
    tenant_id: UUID
    tenant: Tenant
    user_id: UUID
    role: str  # "owner" or "admin"


async def get_tenant_context(
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Get the current mayorista's tenant context.

    This dependency should be added to all routes that need tenant scoping.
    It validates that the mayorista has a tenant and that the tenant is active.

    Raises:
        HTTPException 404: If tenant not found or inactive.
    """
    if mayorista.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not configured for this account",
        )

    tenant_repo = TenantRepo(db)
    tenant = await tenant_repo.get_by_id(mayorista.tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant is not active",
        )

    return TenantContext(
        tenant_id=tenant.id,
        tenant=tenant,
        user_id=mayorista.id,
        role="admin" if mayorista.role == "admin" else "owner",
    )
