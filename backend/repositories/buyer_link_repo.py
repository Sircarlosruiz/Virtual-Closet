"""Data access for BuyerLink entities."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.buyer_link import BuyerLink


class BuyerLinkRepo:
    """Data access for BuyerLink entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, link: BuyerLink) -> BuyerLink:
        self._db.add(link)
        await self._db.commit()
        await self._db.refresh(link)
        return link

    async def get_by_jti(self, jti: str) -> BuyerLink | None:
        result = await self._db.execute(
            select(BuyerLink).where(BuyerLink.token_jti == jti)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[BuyerLink]:
        result = await self._db.execute(
            select(BuyerLink)
            .where(BuyerLink.tenant_id == tenant_id)
            .order_by(BuyerLink.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_expired(self, tenant_id: uuid.UUID) -> list[BuyerLink]:
        result = await self._db.execute(
            select(BuyerLink)
            .where(
                BuyerLink.tenant_id == tenant_id,
                BuyerLink.expires_at < datetime.now(timezone.utc),
            )
            .order_by(BuyerLink.created_at.desc())
        )
        return list(result.scalars().all())
