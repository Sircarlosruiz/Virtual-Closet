from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.composition_snapshot import CompositionSnapshot


class CompositionSnapshotAlreadyExistsError(Exception):
    """Raised when a snapshot already exists for a generation job."""


class CompositionSnapshotRepository:
    """Insert-only: no update method is exposed (ADR-052)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, snapshot: CompositionSnapshot) -> CompositionSnapshot:
        self._db.add(snapshot)
        try:
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            raise CompositionSnapshotAlreadyExistsError(
                f"A snapshot already exists for generation job {snapshot.generation_job_id}"
            ) from exc
        await self._db.refresh(snapshot)
        return snapshot

    async def get_by_generation_job_id(
        self, generation_job_id: UUID
    ) -> CompositionSnapshot | None:
        result = await self._db.execute(
            select(CompositionSnapshot).where(
                CompositionSnapshot.generation_job_id == generation_job_id
            )
        )
        return result.scalar_one_or_none()
