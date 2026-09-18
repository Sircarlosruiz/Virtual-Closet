"""Data access for authenticated service clients."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_client import ServiceClient


class ServiceClientRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, client: ServiceClient) -> ServiceClient:
        self._db.add(client)
        await self._db.commit()
        await self._db.refresh(client)
        return client

    async def get_by_id(self, client_id: UUID) -> ServiceClient | None:
        result = await self._db.execute(
            select(ServiceClient).where(ServiceClient.id == client_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ServiceClient | None:
        result = await self._db.execute(
            select(ServiceClient).where(ServiceClient.name == name)
        )
        return result.scalar_one_or_none()

    async def touch_last_used(self, client_id: UUID) -> None:
        await self._db.execute(
            update(ServiceClient)
            .where(ServiceClient.id == client_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self._db.commit()
