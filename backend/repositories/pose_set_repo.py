import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pose_set import PoseSet


class PoseSetRepo:
    """Ownership-scoped persistence for PoseSet metadata."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, pose_set: PoseSet) -> PoseSet:
        self._db.add(pose_set)
        await self._db.flush()
        return pose_set

    async def get_by_id_and_mayorista(
        self, pose_set_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> PoseSet | None:
        result = await self._db.execute(
            select(PoseSet).where(
                PoseSet.id == pose_set_id,
                PoseSet.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()
