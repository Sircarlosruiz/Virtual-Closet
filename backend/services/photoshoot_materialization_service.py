"""Turn a produced pose image into a publication GenerationJob (ADR-070)."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from models.generation_job import GenerationJob
from models.photoshoot import Photoshoot, PhotoshootResult
from repositories.generation_job_repo import GenerationJobRepository
from repositories.photoshoot_repo import PhotoshootRepository
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


class PhotoshootMaterializationService:
    def __init__(
        self,
        repo: PhotoshootRepository,
        jobs: GenerationJobRepository,
        storage: StorageService,
    ) -> None:
        self._repo = repo
        self._jobs = jobs
        self._storage = storage

    def result_key(self, photoshoot_id: UUID, model_id: UUID, pose_id: UUID) -> str:
        return f"photoshoots/{photoshoot_id}/{model_id}/{pose_id}"

    async def materialize_slot(
        self,
        photoshoot: Photoshoot,
        *,
        model_id: UUID,
        pose_id: UUID,
        pose: str | None,
        source_key: str,
        source_bucket: str = "generated",
    ) -> PhotoshootResult | None:
        existing = await self._repo.get_result_by_slot(photoshoot.id, model_id, pose_id)
        if existing is not None:
            return existing

        dest_key = self.result_key(photoshoot.id, model_id, pose_id)
        try:
            if not await self._storage.object_exists(dest_key, bucket_override="generated"):
                data = await self._storage.get_object_bytes(
                    source_key, bucket_override=source_bucket
                )
                await self._storage.upload_bytes(
                    dest_key,
                    data,
                    content_type="image/png",
                    bucket_override="generated",
                )
        except Exception:
            logger.warning(
                "result_persist_deferred",
                extra={
                    "photoshoot_id": str(photoshoot.id),
                    "model_id": str(model_id),
                    "pose_id": str(pose_id),
                },
            )
            return None

        job = GenerationJob(
            id=uuid4(),
            owner_id=photoshoot.mayorista_id,
            mode="try_on",
            provider="replicate",
            status="completed",
            input_data={
                "photoshoot_id": str(photoshoot.id),
                "model_id": str(model_id),
                "pose_id": str(pose_id),
                "pose": pose,
                "stage": "poses",
            },
            result_key=dest_key,
        )
        await self._jobs.add(job)
        row = PhotoshootResult(
            photoshoot_id=photoshoot.id,
            generation_job_id=job.id,
            model_id=model_id,
            pose_id=pose_id,
            variant_key=photoshoot.variant_key,
        )
        stored = await self._repo.add_result_if_slot_free(row)
        if stored is None:
            return await self._repo.get_result_by_slot(photoshoot.id, model_id, pose_id)
        logger.info(
            "result_materialized",
            extra={
                "photoshoot_id": str(photoshoot.id),
                "generation_job_id": str(job.id),
                "model_id": str(model_id),
                "pose_id": str(pose_id),
            },
        )
        return stored
