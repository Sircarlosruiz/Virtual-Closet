from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.generation_job import GenerationJob


class GenerationJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, job: GenerationJob) -> GenerationJob:
        self._db.add(job)
        await self._db.commit()
        await self._db.refresh(job)
        return job

    async def get_owned(self, job_id: UUID, owner_id: UUID) -> GenerationJob | None:
        result = await self._db.execute(
            select(GenerationJob).where(
                GenerationJob.id == job_id,
                GenerationJob.owner_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        error_code: str | None = None,
        result_key: str | None = None,
    ) -> GenerationJob | None:
        await self._db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(status=status, error_code=error_code, result_key=result_key)
        )
        await self._db.commit()
        result = await self._db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
        return result.scalar_one_or_none()
