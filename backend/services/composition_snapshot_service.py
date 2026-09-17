from uuid import UUID

from api.schemas.composition_snapshot import EffectiveConfiguration
from api.schemas.image_generation import GenerationProvider, ImageGenerationRequest
from models.composition_snapshot import CompositionSnapshot
from models.generation_job import GenerationJob
from models.image_template import ImageTemplate
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from services.image_generation_service import ImageGenerationService
from services.storage_service import StorageService

_REFERENCE_BUCKET = "originals"


class CompositionSnapshotNotFoundError(Exception):
    pass


class TemplateReferenceUnavailableError(Exception):
    """Raised when a template reference is missing from durable storage."""


class CompositionSnapshotService:
    def __init__(
        self,
        repository: CompositionSnapshotRepository,
        generation_service: ImageGenerationService,
        storage_service: StorageService | None = None,
    ) -> None:
        self._repository = repository
        self._generation_service = generation_service
        self._storage_service = storage_service or StorageService()

    async def capture_snapshot(
        self, job: GenerationJob, template: ImageTemplate
    ) -> CompositionSnapshot:
        """Freezes the template's current fields and reference keys.

        Fails with `TemplateReferenceUnavailableError` rather than persisting
        a partial snapshot if a reference is missing from storage.
        """
        reference_keys = [ref.storage_key for ref in template.references]
        for key in reference_keys:
            if not await self._storage_service.object_exists(
                key, bucket_override=_REFERENCE_BUCKET
            ):
                raise TemplateReferenceUnavailableError(
                    f"Template reference '{key}' is unavailable in storage"
                )

        config = EffectiveConfiguration(
            model=template.model,
            background=template.background,
            colors=template.colors,
            rack=template.rack,
            prompt=template.prompt,
            provider=job.provider,
            reference_keys=reference_keys,
            template_version=template.version,
        )
        snapshot = CompositionSnapshot(
            generation_job_id=job.id,
            template_id=template.id,
            template_version=template.version,
            effective_configuration=config.model_dump(),
        )
        return await self._repository.save(snapshot)

    async def get_snapshot(self, generation_job_id: UUID) -> CompositionSnapshot:
        snapshot = await self._repository.get_by_generation_job_id(generation_job_id)
        if snapshot is None:
            raise CompositionSnapshotNotFoundError(
                f"No snapshot found for generation job {generation_job_id}"
            )
        return snapshot

    async def regenerate(
        self, source_job: GenerationJob, snapshot: CompositionSnapshot
    ) -> GenerationJob:
        """Creates a new job/result from a frozen snapshot without altering the original."""
        reference_keys = snapshot.effective_configuration.get("reference_keys", [])
        for key in reference_keys:
            if not await self._storage_service.object_exists(
                key, bucket_override=_REFERENCE_BUCKET
            ):
                raise TemplateReferenceUnavailableError(
                    f"Template reference '{key}' is no longer available in storage"
                )

        request = ImageGenerationRequest(
            **source_job.input_data,
            provider=GenerationProvider(source_job.provider),
        )
        new_job, _ = await self._generation_service.create_job(
            source_job.owner_id, request
        )
        return new_job
