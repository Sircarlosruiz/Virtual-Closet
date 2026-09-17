import uuid
from dataclasses import dataclass
from uuid import UUID

from repositories.generation_job_repo import GenerationJobRepository


@dataclass(frozen=True)
class ConcurrencyLease:
    job_id: UUID
    holder_token: UUID


class ConcurrencyGuardService:
    """Acquires/releases the per-job execution lease.

    Fails closed: if the lease is already held (duplicate delivery, or a
    concurrent worker), acquisition returns None and no provider call is
    started.
    """

    def __init__(self, repository: GenerationJobRepository) -> None:
        self._repository = repository

    async def acquire(self, job_id: UUID) -> ConcurrencyLease | None:
        token = uuid.uuid4()
        acquired = await self._repository.try_acquire_lease(job_id, token)
        if not acquired:
            return None
        return ConcurrencyLease(job_id=job_id, holder_token=token)

    async def release(self, lease: ConcurrencyLease) -> None:
        await self._repository.release_lease(lease.job_id, lease.holder_token)
