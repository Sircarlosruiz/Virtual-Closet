import uuid
from datetime import datetime, timezone

from core.celery_app import app as celery_app
from core.config import settings
from core.minio_client import MinIOClient
from models.tryoff_job import SourceImage, TryoffJob
from repositories.tryoff_job_repo import SourceImageRepo, TryoffJobRepo


class SourceImageNotFoundError(Exception):
    """Raised when a source image does not exist."""


class SourceImageOwnershipError(Exception):
    """Raised when a source image does not belong to the requesting mayorista."""


class TryoffJobNotFoundError(Exception):
    """Raised when a TryOff job does not exist."""


class TryoffJobOwnershipError(Exception):
    """Raised when a TryOff job does not belong to the requesting mayorista."""


class TryoffJobService:
    """Handles TryOff job submission and status retrieval."""

    def __init__(
        self,
        tryoff_job_repo: TryoffJobRepo,
        source_image_repo: SourceImageRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._tryoff_job_repo = tryoff_job_repo
        self._source_image_repo = source_image_repo
        self._minio = minio_client

    async def submit_job(
        self,
        mayorista_id: uuid.UUID,
        source_image_id: uuid.UUID,
        garment_type: str,
    ) -> TryoffJob:
        """Submit a new TryOff extraction job.

        Validates source image ownership, creates the job record, and publishes
        a Celery task.

        Raises:
            SourceImageNotFoundError: If source image doesn't exist.
            SourceImageOwnershipError: If source image doesn't belong to mayorista.
        """
        # Validate source image ownership
        source_image = await self._source_image_repo.get_by_id(
            source_image_id, mayorista_id
        )
        if source_image is None:
            raise SourceImageNotFoundError("Source image not found")

        # Create job record
        max_retries = getattr(settings, "TRYOFF_MAX_RETRIES", 2)
        job = TryoffJob(
            mayorista_id=mayorista_id,
            source_image_id=source_image_id,
            garment_type=garment_type,
            status="pending",
            retry_count=0,
            max_retries=max_retries,
        )
        job = await self._tryoff_job_repo.create(job)

        # Publish Celery task
        celery_app.send_task(
            "tasks.tryoff_task.process_tryoff_job",
            args=[str(job.id)],
            queue="tryoff",
        )

        return job

    async def submit_batch(
        self,
        mayorista_id: uuid.UUID,
        source_image_id: uuid.UUID,
        garment_types: list[str],
    ) -> list[TryoffJob]:
        """Submit multiple TryOff jobs for different garment types from the same source image.

        De-duplicates garment types and creates one job per unique type.

        Raises:
            SourceImageNotFoundError: If source image doesn't exist.
            SourceImageOwnershipError: If source image doesn't belong to mayorista.
        """
        # Validate source image ownership
        source_image = await self._source_image_repo.get_by_id(
            source_image_id, mayorista_id
        )
        if source_image is None:
            raise SourceImageNotFoundError("Source image not found")

        # De-duplicate garment types
        unique_types = list(dict.fromkeys(garment_types))

        # Create job records
        max_retries = getattr(settings, "TRYOFF_MAX_RETRIES", 2)
        jobs = [
            TryoffJob(
                mayorista_id=mayorista_id,
                source_image_id=source_image_id,
                garment_type=gt,
                status="pending",
                retry_count=0,
                max_retries=max_retries,
            )
            for gt in unique_types
        ]
        jobs = await self._tryoff_job_repo.create_batch(jobs)

        # Publish Celery tasks
        for job in jobs:
            celery_app.send_task(
                "tasks.tryoff_task.process_tryoff_job",
                args=[str(job.id)],
                queue="tryoff",
            )

        return jobs

    async def get_job_status(
        self,
        job_id: uuid.UUID,
        mayorista_id: uuid.UUID,
    ) -> dict:
        """Get the current status of a TryOff job.

        Returns a dict with job status info including a fresh presigned
        URL for the result if the job is complete.

        Raises:
            TryoffJobNotFoundError: If job doesn't exist.
            TryoffJobOwnershipError: If job doesn't belong to mayorista.
        """
        job = await self._tryoff_job_repo.get_by_id_and_mayorista(
            job_id, mayorista_id
        )
        if job is None:
            # Check if it exists at all
            exists = await self._tryoff_job_repo.get_by_id(job_id)
            if exists is None:
                raise TryoffJobNotFoundError("Job not found")
            raise TryoffJobOwnershipError("You do not own this job")

        result: dict = {
            "job_id": job.id,
            "status": job.status,
            "garment_type": job.garment_type,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result_url": None,
            "error_reason": job.error_reason,
            "retry_count": job.retry_count,
        }

        # Generate fresh presigned URL for complete jobs
        if job.status == "complete" and job.output_minio_key:
            result["result_url"] = await self._minio.get_presigned_url(
                bucket="generated", key=job.output_minio_key
            )

        return result

    async def list_jobs(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """List mayorista's TryOff jobs with pagination.

        Returns a list of job status dicts (same format as get_job_status)
        and the total count.
        """
        jobs, total = await self._tryoff_job_repo.list_by_mayorista(
            mayorista_id, page, page_size
        )
        results = []
        for job in jobs:
            item: dict = {
                "job_id": job.id,
                "status": job.status,
                "garment_type": job.garment_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "result_url": None,
                "error_reason": job.error_reason,
                "retry_count": job.retry_count,
            }
            if job.status == "complete" and job.output_minio_key:
                item["result_url"] = await self._minio.get_presigned_url(
                    bucket="generated", key=job.output_minio_key
                )
            results.append(item)
        return results, total
