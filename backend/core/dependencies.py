from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from models.mayorista import Mayorista
from services.token_service import TokenService
from repositories.customer_repo import CustomerRepo


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

    from uuid import UUID

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
    from uuid import UUID

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
