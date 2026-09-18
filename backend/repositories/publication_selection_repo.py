"""Data access for staff publication selections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.publication import PublicationSelection


class PublicationSelectionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, selection: PublicationSelection) -> PublicationSelection:
        self._db.add(selection)
        await self._db.flush()
        await self._db.refresh(selection)
        return selection

    async def get_by_id(self, selection_id: UUID) -> PublicationSelection | None:
        result = await self._db.execute(
            select(PublicationSelection).where(PublicationSelection.id == selection_id)
        )
        return result.scalar_one_or_none()

    async def get_by_candidate(
        self,
        product_link_id: UUID,
        generation_job_id: UUID,
        composition_version_id: UUID | None,
    ) -> PublicationSelection | None:
        stmt = select(PublicationSelection).where(
            PublicationSelection.product_link_id == product_link_id,
            PublicationSelection.generation_job_id == generation_job_id,
        )
        if composition_version_id is None:
            stmt = stmt.where(PublicationSelection.composition_version_id.is_(None))
        else:
            stmt = stmt.where(
                PublicationSelection.composition_version_id == composition_version_id
            )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_job_and_link(
        self, product_link_id: UUID, generation_job_id: UUID
    ) -> list[PublicationSelection]:
        result = await self._db.execute(
            select(PublicationSelection).where(
                PublicationSelection.product_link_id == product_link_id,
                PublicationSelection.generation_job_id == generation_job_id,
            )
        )
        return list(result.scalars().all())
