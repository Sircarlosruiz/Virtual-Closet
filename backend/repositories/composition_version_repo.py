from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.product_overlay import CompositionVersion


class CompositionVersionConflictError(Exception):
    """Raised when a deterministic spec hash already exists for the overlay."""


class CompositionVersionRepository:
    """Append-only: no update or delete method is exposed (ADR-055)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def append(self, version: CompositionVersion) -> CompositionVersion:
        self._db.add(version)
        try:
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            raise CompositionVersionConflictError(
                f"A composition version already exists for overlay {version.overlay_id} "
                f"with spec hash {version.spec_hash}"
            ) from exc
        await self._db.refresh(version)
        return version

    async def get_by_id(self, version_id: UUID) -> CompositionVersion | None:
        result = await self._db.execute(
            select(CompositionVersion).where(CompositionVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_overlay(
        self, overlay_id: UUID
    ) -> CompositionVersion | None:
        result = await self._db.execute(
            select(CompositionVersion)
            .where(CompositionVersion.overlay_id == overlay_id)
            .order_by(CompositionVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_overlay(self, overlay_id: UUID) -> list[CompositionVersion]:
        result = await self._db.execute(
            select(CompositionVersion)
            .where(CompositionVersion.overlay_id == overlay_id)
            .order_by(CompositionVersion.version.desc())
        )
        return list(result.scalars().all())

    async def find_by_spec_hash(
        self, overlay_id: UUID, spec_hash: str
    ) -> CompositionVersion | None:
        result = await self._db.execute(
            select(CompositionVersion).where(
                CompositionVersion.overlay_id == overlay_id,
                CompositionVersion.spec_hash == spec_hash,
            )
        )
        return result.scalar_one_or_none()
