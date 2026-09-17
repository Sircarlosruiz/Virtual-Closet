from datetime import datetime, timezone
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

    async def get_by_id(self, job_id: UUID) -> GenerationJob | None:
        result = await self._db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
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

    async def find_by_idempotency_key(
        self, owner_id: UUID, idempotency_key: str
    ) -> GenerationJob | None:
        result = await self._db.execute(
            select(GenerationJob).where(
                GenerationJob.owner_id == owner_id,
                GenerationJob.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def try_acquire_lease(self, job_id: UUID, holder_token: UUID) -> bool:
        """Atomic conditional UPDATE — fails closed if a lease is already held.

        Mirrors the atomic-UPDATE-expression pattern used for batch counters
        (ADR-009, ADR-021) rather than a Redis lock (ADR-050).
        """
        result = await self._db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.lock_token.is_(None))
            .values(lock_token=holder_token, locked_at=datetime.now(timezone.utc))
        )
        await self._db.commit()
        return result.rowcount == 1

    async def release_lease(self, job_id: UUID, holder_token: UUID) -> None:
        await self._db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.lock_token == holder_token)
            .values(lock_token=None, locked_at=None)
        )
        await self._db.commit()

    async def increment_retry_count(self, job_id: UUID) -> None:
        await self._db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(retry_count=GenerationJob.retry_count + 1)
        )
        await self._db.commit()

    async def update_usage(
        self,
        job_id: UUID,
        usage_status: str,
        usage_model: str | None,
        usage_call_count: int | None,
    ) -> None:
        await self._db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(
                usage_status=usage_status,
                usage_model=usage_model,
                usage_call_count=usage_call_count,
            )
        )
        await self._db.commit()
