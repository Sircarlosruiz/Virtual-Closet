from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.product_overlay import ProductOverlay


class ProductOverlayRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, overlay: ProductOverlay) -> ProductOverlay:
        self._db.add(overlay)
        await self._db.commit()
        await self._db.refresh(overlay)
        return overlay

    async def get_by_id(self, overlay_id: UUID) -> ProductOverlay | None:
        result = await self._db.execute(
            select(ProductOverlay).where(ProductOverlay.id == overlay_id)
        )
        return result.scalar_one_or_none()

    async def get_by_generation_job_id(
        self, generation_job_id: UUID
    ) -> ProductOverlay | None:
        result = await self._db.execute(
            select(ProductOverlay).where(
                ProductOverlay.generation_job_id == generation_job_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_generation_job_id_for_update(
        self, generation_job_id: UUID
    ) -> ProductOverlay | None:
        """Row-locks the overlay so version numbers serialize.

        Mirrors the row-lock pattern used for template version bumps in bolt
        045; the lock is held until the appending transaction commits.
        """
        result = await self._db.execute(
            select(ProductOverlay)
            .where(ProductOverlay.generation_job_id == generation_job_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()
