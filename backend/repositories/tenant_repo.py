"""Data access for Tenant entities."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.tenant import Tenant


class TenantRepo:
    """Data access for Tenant entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, tenant: Tenant) -> Tenant:
        self._db.add(tenant)
        await self._db.commit()
        await self._db.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        result = await self._db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none()

    async def exists_by_slug(self, slug: str) -> bool:
        result = await self._db.execute(
            select(func.count(Tenant.id)).where(Tenant.slug == slug)
        )
        return (result.scalar() or 0) > 0

    async def update(self, tenant: Tenant) -> Tenant:
        await self._db.commit()
        await self._db.refresh(tenant)
        return tenant

    async def update_name(
        self, tenant_id: uuid.UUID, new_name: str
    ) -> Tenant | None:
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(name=new_name, updated_at=func.now())
            .returning(Tenant)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def update_settings(
        self, tenant_id: uuid.UUID, settings: dict
    ) -> Tenant | None:
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(settings=settings, updated_at=func.now())
            .returning(Tenant)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def deactivate(self, tenant_id: uuid.UUID) -> Tenant | None:
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(is_active=False, updated_at=func.now())
            .returning(Tenant)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Tenant]:
        result = await self._db.execute(
            select(Tenant)
            .where(Tenant.is_active == True)
            .order_by(Tenant.created_at)
        )
        return list(result.scalars().all())
