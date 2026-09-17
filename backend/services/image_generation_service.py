from uuid import UUID

from api.schemas.image_generation import GenerationProvider, ImageGenerationRequest
from models.generation_job import GenerationJob
from repositories.generation_job_repo import GenerationJobRepository
from services.idempotency_service import IdempotencyService, compute_payload_fingerprint


class ImageGenerationService:
    def __init__(
        self,
        repository: GenerationJobRepository,
        idempotency_service: IdempotencyService | None = None,
    ) -> None:
        self._repository = repository
        self._idempotency_service = idempotency_service or IdempotencyService(repository)

    async def create_job(
        self,
        owner_id: UUID,
        request: ImageGenerationRequest,
        idempotency_key: str | None = None,
    ) -> tuple[GenerationJob, bool]:
        """Returns (job, created). `created` is False for an idempotent replay."""
        provider = request.provider or GenerationProvider.openai
        input_data = request.model_dump(mode="json", exclude_none=True)
        input_data.pop("provider", None)

        payload_fingerprint: str | None = None
        if idempotency_key:
            payload_fingerprint = compute_payload_fingerprint(input_data)
            existing = await self._idempotency_service.find_existing(
                owner_id, idempotency_key, payload_fingerprint
            )
            if existing is not None:
                return existing, False

        job = GenerationJob(
            owner_id=owner_id,
            mode=request.mode.value,
            provider=provider.value,
            status="queued",
            input_data=input_data,
            idempotency_key=idempotency_key,
            payload_fingerprint=payload_fingerprint,
        )
        job = await self._repository.create(job)
        return job, True

    async def get_job(self, job_id: UUID, owner_id: UUID) -> GenerationJob | None:
        return await self._repository.get_owned(job_id, owner_id)
