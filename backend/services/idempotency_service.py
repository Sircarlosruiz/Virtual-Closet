import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from models.generation_job import GenerationJob
from repositories.generation_job_repo import GenerationJobRepository


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused with a different payload."""


@dataclass(frozen=True)
class IdempotencyResolution:
    job: GenerationJob
    created: bool


def compute_payload_fingerprint(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class IdempotencyService:
    """Resolves an idempotency key to an existing or new GenerationJob.

    Same (key, payload) always resolves to the same job. Same key with a
    different payload is a conflict, never a silent overwrite.
    """

    def __init__(self, repository: GenerationJobRepository) -> None:
        self._repository = repository

    async def find_existing(
        self, owner_id: UUID, idempotency_key: str, payload_fingerprint: str
    ) -> GenerationJob | None:
        existing = await self._repository.find_by_idempotency_key(owner_id, idempotency_key)
        if existing is None:
            return None
        if existing.payload_fingerprint != payload_fingerprint:
            raise IdempotencyConflictError(
                "Idempotency key already used with a different request payload"
            )
        return existing
