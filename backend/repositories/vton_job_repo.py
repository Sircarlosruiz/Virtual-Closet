import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.vton_job import VTONJob


class VTONJobRepo:
    """Data access for VTONJob entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, job: VTONJob, *, commit: bool = True) -> VTONJob:
        self._db.add(job)
        await self._db.flush()
        if commit:
            await self._db.commit()
            await self._db.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> VTONJob | None:
        result = await self._db.execute(
            select(VTONJob).where(VTONJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_mayorista(
        self, job_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> VTONJob | None:
        result = await self._db.execute(
            select(VTONJob).where(
                VTONJob.id == job_id,
                VTONJob.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: uuid.UUID,
        new_status: str,
        **kwargs,
    ) -> VTONJob | None:
        """Atomically update job status with optional additional fields."""
        stmt = (
            select(VTONJob)
            .where(VTONJob.id == job_id)
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
    ) -> tuple[list[VTONJob], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count(VTONJob.id)).where(
            VTONJob.mayorista_id == mayorista_id
        )
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = (
            select(VTONJob)
            .where(VTONJob.mayorista_id == mayorista_id)
            .order_by(VTONJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(list_stmt)
        items = list(result.scalars().all())
        return items, total
