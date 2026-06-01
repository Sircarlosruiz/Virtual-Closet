import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tryoff_job import SourceImage, TryoffJob


class SourceImageRepo:
    """Data access for SourceImage entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, source_image: SourceImage) -> SourceImage:
        self._db.add(source_image)
        await self._db.commit()
        await self._db.refresh(source_image)
        return source_image

    async def get_by_id(
        self, image_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> SourceImage | None:
        result = await self._db.execute(
            select(SourceImage).where(
                SourceImage.id == image_id,
                SourceImage.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_mayorista(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SourceImage], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(SourceImage.id)).where(
            SourceImage.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(SourceImage)
            .where(SourceImage.mayorista_id == mayorista_id)
            .order_by(SourceImage.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total


class TryoffJobRepo:
    """Data access for TryoffJob entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, job: TryoffJob) -> TryoffJob:
        self._db.add(job)
        await self._db.commit()
        await self._db.refresh(job)
        return job

    async def create_batch(self, jobs: list[TryoffJob]) -> list[TryoffJob]:
        self._db.add_all(jobs)
        await self._db.commit()
        for job in jobs:
            await self._db.refresh(job)
        return jobs

    async def get_by_id(self, job_id: uuid.UUID) -> TryoffJob | None:
        result = await self._db.execute(
            select(TryoffJob).where(TryoffJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_mayorista(
        self, job_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> TryoffJob | None:
        result = await self._db.execute(
            select(TryoffJob).where(
                TryoffJob.id == job_id,
                TryoffJob.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: uuid.UUID,
        new_status: str,
        **kwargs,
    ) -> TryoffJob | None:
        """Atomically update job status with optional additional fields."""
        stmt = (
            select(TryoffJob)
            .where(TryoffJob.id == job_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = new_status
        for key, value in kwargs.items():
            setattr(job, key, value)

        await self._db.commit()
        await self._db.refresh(job)
        return job

    async def list_by_mayorista(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TryoffJob], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(TryoffJob.id)).where(
            TryoffJob.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(TryoffJob)
            .where(TryoffJob.mayorista_id == mayorista_id)
            .order_by(TryoffJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total
