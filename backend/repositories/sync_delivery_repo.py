"""Data access for per-destination publication deliveries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.publication import SyncDelivery


class SyncDeliveryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, delivery: SyncDelivery) -> SyncDelivery:
        self._db.add(delivery)
        await self._db.flush()
        await self._db.refresh(delivery)
        return delivery

    async def get_by_selection_and_destination(
        self, publication_selection_id: UUID, destination: str
    ) -> SyncDelivery | None:
        result = await self._db.execute(
            select(SyncDelivery).where(
                SyncDelivery.publication_selection_id == publication_selection_id,
                SyncDelivery.destination == destination,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_selection(
        self, publication_selection_id: UUID
    ) -> list[SyncDelivery]:
        result = await self._db.execute(
            select(SyncDelivery)
            .where(SyncDelivery.publication_selection_id == publication_selection_id)
            .order_by(SyncDelivery.destination)
        )
        return list(result.scalars().all())
