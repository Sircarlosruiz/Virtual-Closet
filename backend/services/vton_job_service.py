import uuid
from datetime import datetime, timezone

from core.celery_app import app as celery_app
from core.config import settings
from core.minio_client import MinIOClient
from models.vton_job import VTONJob
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from repositories.vton_job_repo import VTONJobRepo


class PhotoOwnershipError(Exception):
    """Raised when a photo does not belong to the requesting mayorista."""


class PhotoNotFoundError(Exception):
    """Raised when a referenced photo does not exist."""


class VTONJobService:
    """Handles VTON job submission and status retrieval."""

    def __init__(
        self,
        vton_job_repo: VTONJobRepo,
        garment_repo: GarmentPhotoRepo,
        model_repo: ModelPhotoRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._vton_job_repo = vton_job_repo
        self._garment_repo = garment_repo
        self._model_repo = model_repo
        self._minio = minio_client

    async def submit_job(
        self,
        mayorista_id: uuid.UUID,
        garment_photo_id: uuid.UUID,
        model_photo_id: uuid.UUID,
        cloth_type: str,
    ) -> tuple[VTONJob, str]:
        """Submit a new VTON generation job.

        Validates photo ownership, creates the job record, and publishes
        a Celery task. Returns the job and a presigned URL for the garment.

        Raises:
            PhotoNotFoundError: If garment or model photo doesn't exist.
            PhotoOwnershipError: If garment doesn't belong to mayorista.
        """
        # Validate garment ownership
        garment = await self._garment_repo.get_by_id_and_mayorista(
            garment_photo_id, mayorista_id
        )
        if garment is None:
            # Check if it exists at all (for better error message)
            exists = await self._garment_repo.get_by_id(garment_photo_id)
            if exists is None:
                raise PhotoNotFoundError("Garment photo not found")
            raise PhotoOwnershipError("You do not own this garment photo")

        # Validate model photo (can be own or curated)
        model = await self._model_repo.get_by_id(model_photo_id)
        if model is None:
            raise PhotoNotFoundError("Model photo not found")

        # If it's an own model, verify ownership
        if not model.is_curated and model.mayorista_id != mayorista_id:
            raise PhotoOwnershipError("You do not own this model photo")

        # Create job record
        max_retries = getattr(settings, "VTON_MAX_RETRIES", 3)
        job = VTONJob(
            mayorista_id=mayorista_id,
            garment_photo_id=garment_photo_id,
            model_photo_id=model_photo_id,
            cloth_type=cloth_type,
            status="queued",
            retry_count=0,
            max_retries=max_retries,
        )
        job = await self._vton_job_repo.create(job)

        # Publish Celery task
        celery_app.send_task(
            "tasks.vton_task.process_vton_job",
            args=[str(job.id)],
            queue="vton.generation.normal",
        )

        # Generate presigned URL for garment (for response)
        presigned_url = await self._minio.get_presigned_url(
            bucket="originals", key=garment.minio_key
        )

        return job, presigned_url

    async def get_job_status(
        self,
        job_id: uuid.UUID,
        mayorista_id: uuid.UUID,
    ) -> dict:
        """Get the current status of a VTON job.

        Returns a dict with job status info including a fresh presigned
        URL for the result if the job is completed.

        Raises:
            PhotoNotFoundError: If job doesn't exist.
            PhotoOwnershipError: If job doesn't belong to mayorista.
        """
        job = await self._vton_job_repo.get_by_id_and_mayorista(
            job_id, mayorista_id
        )
        if job is None:
            # Check if it exists at all
            exists = await self._vton_job_repo.get_by_id(job_id)
            if exists is None:
                raise PhotoNotFoundError("Job not found")
            raise PhotoOwnershipError("You do not own this job")

        result: dict = {
            "job_id": job.id,
            "status": job.status,
            "cloth_type": job.cloth_type,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result_url": None,
            "error_reason": job.error_reason,
            "retry_count": job.retry_count,
        }

        # Generate fresh presigned URL for completed jobs
        if job.status == "completed" and job.result_minio_key:
            result["result_url"] = await self._minio.get_presigned_url(
                bucket="generated", key=job.result_minio_key
            )

        return result

    async def list_jobs(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """List mayorista's VTON jobs with pagination.

        Returns a list of job status dicts (same format as get_job_status)
        and the total count.
        """
        jobs, total = await self._vton_job_repo.list_by_mayorista(
            mayorista_id, page, page_size
        )
        results = []
        for job in jobs:
            item: dict = {
                "job_id": job.id,
                "status": job.status,
                "cloth_type": job.cloth_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "result_url": None,
                "error_reason": job.error_reason,
                "retry_count": job.retry_count,
            }
            if job.status == "completed" and job.result_minio_key:
                item["result_url"] = await self._minio.get_presigned_url(
                    bucket="generated", key=job.result_minio_key
                )
            results.append(item)
        return results, total
