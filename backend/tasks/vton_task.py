import uuid
from datetime import datetime, timezone

from core.celery_app import app
from core.config import settings
from core.minio_client import MinIOClient
from services.providers.vton_provider import get_vton_provider
from services.retry_policy import RetryPolicy, is_retriable_error


@app.task(
    bind=True,
    name="tasks.vton_task.process_vton_job",
    acks_late=True,
    queue="vton.generation.normal",
)
def process_vton_job(self, job_id: str) -> None:
    """Celery task that processes a single VTON job with automatic retry.

    Flow:
    1. Re-read job from DB — confirm status=queued (idempotency guard)
    2. Update status → processing, set started_at
    3. Get garment and model presigned URLs from MinIO
    4. Call VTONProvider.generate(garment_url, model_url, cloth_type)
    5. Upload result to MinIO at results/{mayorista_id}/{job_id}.jpg
    6. Update status → completed, set result_minio_key, completed_at

    On error:
    - If retriable and retries remain: increment retry_count, reset to queued,
      re-queue with exponential backoff
    - If retriable but max retries exceeded: mark as failed
    - If non-retriable: mark as failed immediately
    """
    import asyncio

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from models.vton_job import VTONJob

    # Sync DB connection for Celery worker
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    Session = sessionmaker(engine)

    minio = MinIOClient()
    retry_policy = RetryPolicy()

    with Session() as session:
        # Step 1: Re-read job — idempotency guard
        result = session.execute(
            select(VTONJob).where(VTONJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"VTONJob {job_id} not found")

        if job.status != "queued":
            # Already being processed or completed — skip (idempotency)
            return

        # Step 2: Update status → processing
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        try:
            # Step 3: Get presigned URLs for garment and model
            garment_url = asyncio.run(
                minio.get_presigned_url(
                    bucket="originals", key=job.garment_photo.minio_key
                )
            )
            model_url = asyncio.run(
                minio.get_presigned_url(
                    bucket="originals", key=job.model_photo.minio_key
                )
            )

            # Step 4: Call VTON provider
            provider = get_vton_provider()
            result_bytes = asyncio.run(
                provider.generate(garment_url, model_url, job.cloth_type)
            )

            # Step 5: Upload result to MinIO
            result_key = f"results/{job.mayorista_id}/{job_id}.jpg"
            asyncio.run(
                minio.upload_file(
                    bucket="generated",
                    key=result_key,
                    data=result_bytes,
                    content_type="image/jpeg",
                )
            )

            # Step 6: Update status → completed
            job.status = "completed"
            job.result_minio_key = result_key
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            # Refresh job from DB to get latest state
            session.refresh(job)

            if is_retriable_error(exc):
                if retry_policy.should_retry(job.retry_count):
                    # Schedule retry with exponential backoff
                    delay = retry_policy.get_delay(job.retry_count)
                    job.retry_count += 1
                    job.status = "queued"
                    job.error_reason = str(exc)[:500]
                    session.commit()

                    # Re-queue with countdown (exponential backoff)
                    self.retry(exc=exc, countdown=delay)
                else:
                    # Max retries exceeded → permanently failed
                    job.status = "failed"
                    job.error_reason = (
                        f"Failed after {job.max_retries} retries: {exc}"
                    )[:500]
                    job.completed_at = datetime.now(timezone.utc)
                    session.commit()
            else:
                # Non-retriable error → fail immediately
                job.status = "failed"
                job.error_reason = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
