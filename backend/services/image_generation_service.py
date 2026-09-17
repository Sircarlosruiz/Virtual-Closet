from uuid import UUID

from api.schemas.image_generation import ImageGenerationRequest, GenerationProvider
from models.generation_job import GenerationJob
from repositories.generation_job_repo import GenerationJobRepository


class ImageGenerationService:
    def __init__(self, repository: GenerationJobRepository) -> None:
        self._repository = repository

    async def create_job(
        self, owner_id: UUID, request: ImageGenerationRequest
    ) -> GenerationJob:
        provider = request.provider or GenerationProvider.openai
        input_data = request.model_dump(mode="json", exclude_none=True)
        input_data.pop("provider", None)
        job = GenerationJob(
            owner_id=owner_id,
            mode=request.mode.value,
            provider=provider.value,
            status="queued",
            input_data=input_data,
        )
        return await self._repository.create(job)

    async def get_job(self, job_id: UUID, owner_id: UUID) -> GenerationJob | None:
        return await self._repository.get_owned(job_id, owner_id)
