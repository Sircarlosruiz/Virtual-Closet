from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.provider_invocation import ProviderInvocation


class ProviderInvocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, invocation: ProviderInvocation) -> ProviderInvocation:
        self._db.add(invocation)
        await self._db.commit()
        await self._db.refresh(invocation)
        return invocation

    async def list_by_job(self, job_id: UUID) -> list[ProviderInvocation]:
        result = await self._db.execute(
            select(ProviderInvocation)
            .where(ProviderInvocation.job_id == job_id)
            .order_by(ProviderInvocation.attempt_number)
        )
        return list(result.scalars().all())

    async def count_by_job(self, job_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count(ProviderInvocation.id)).where(
                ProviderInvocation.job_id == job_id
            )
        )
        return result.scalar() or 0

    async def mark_completed(
        self,
        invocation_id: UUID,
        status: str,
        error_code: str | None,
        error_category: str | None,
        retryable: bool | None,
        usage_status: str,
        usage_model: str | None,
        usage_call_count: int | None,
        usage_raw: dict | None,
        completed_at,
    ) -> ProviderInvocation | None:
        result = await self._db.execute(
            select(ProviderInvocation).where(ProviderInvocation.id == invocation_id)
        )
        invocation = result.scalar_one_or_none()
        if invocation is None:
            return None
        invocation.status = status
        invocation.error_code = error_code
        invocation.error_category = error_category
        invocation.retryable = retryable
        invocation.usage_status = usage_status
        invocation.usage_model = usage_model
        invocation.usage_call_count = usage_call_count
        invocation.usage_raw = usage_raw
        invocation.completed_at = completed_at
        await self._db.commit()
        await self._db.refresh(invocation)
        return invocation
