from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from models.mayorista import Mayorista


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
