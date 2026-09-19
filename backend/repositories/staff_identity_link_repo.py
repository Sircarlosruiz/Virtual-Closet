"""Data access for staff identity links (external staff → Mayorista mirror)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.staff_identity_link import StaffIdentityLink


class StaffIdentityLinkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_system_and_external_staff(
        self, system: str, external_staff_id: str
    ) -> StaffIdentityLink | None:
        result = await self._db.execute(
            select(StaffIdentityLink).where(
                StaffIdentityLink.system == system,
                StaffIdentityLink.external_staff_id == external_staff_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_mayorista(
        self, system: str, tenant_id: UUID, mayorista_id: UUID
    ) -> StaffIdentityLink | None:
        result = await self._db.execute(
            select(StaffIdentityLink).where(
                StaffIdentityLink.system == system,
                StaffIdentityLink.tenant_id == tenant_id,
                StaffIdentityLink.mayorista_id == mayorista_id,
                StaffIdentityLink.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def add(self, link: StaffIdentityLink) -> StaffIdentityLink:
        self._db.add(link)
        await self._db.flush()
        return link

    async def save(self, link: StaffIdentityLink) -> StaffIdentityLink:
        await self._db.flush()
        return link
