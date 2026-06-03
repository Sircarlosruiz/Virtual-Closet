import uuid
from datetime import datetime, timezone

from core.celery_app import app
from core.config import settings
from core.minio_client import MinIOClient
from services.tryoff_model_client import TryoffModelClient, TryoffModelClientError


@app.task(
    bind=True,
    name="tasks.tryoff_task.process_tryoff_job",
    acks_late=True,
    queue="tryoff",
)
def process_tryoff_job(self, job_id: str) -> None:
    """Celery task that processes a single TryOff job with automatic retry.

    Flow:
    1. Re-read job from DB — confirm status=pending (idempotency guard)
    2. Update status → processing, set started_at
    3. Get source image presigned URL from MinIO
    4. Call TryoffModelClient.extract_garment(source_url, garment_type)
    5. Upload result to MinIO at media/{mayorista_id}/extracted/{job_id}.png
    6. Create MediaItem in media library
    7. Update status → complete, set output_minio_key, completed_at

    On error:
    - If retriable and retries remain: increment retry_count, reset to pending,
      re-queue with exponential backoff
    - If non-retriable: mark as failed immediately
    """
    import asyncio

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import joinedload, sessionmaker

    import models  # noqa: F401 — register all ORM mappers (SourceImage, TryoffJob, …)

    from models.media import MediaItem
    from models.tryoff_job import TryoffJob

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    Session = sessionmaker(engine)

    minio = MinIOClient()
    model_client = TryoffModelClient()

    with Session() as session:
        result = session.execute(
            select(TryoffJob)
            .options(joinedload(TryoffJob.source_image))
            .where(TryoffJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"TryoffJob {job_id} not found")

        if job.status != "pending":
            return

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        try:
            source_url = asyncio.run(
                minio.get_presigned_url(
                    bucket="originals",
                    key=job.source_image.minio_key,
                    for_browser=False,
                )
            )

            result_bytes = asyncio.run(
                model_client.extract_garment(source_url, job.garment_type)
            )

            output_key = f"media/{job.mayorista_id}/extracted/{job_id}.png"
            asyncio.run(
                minio.upload_file(
                    bucket="generated",
                    key=output_key,
                    data=result_bytes,
                    content_type="image/png",
                )
            )

            media_item = MediaItem(
                mayorista_id=job.mayorista_id,
                minio_key=output_key,
                media_type="extracted_garment",
                filename=f"{job_id}.png",
                content_type="image/png",
                size_bytes=len(result_bytes),
                item_metadata={
                    "type": "extracted_garment",
                    "garment_type": job.garment_type,
                    "source_job_id": str(job.id),
                    "source_image_id": str(job.source_image_id),
                },
            )
            session.add(media_item)
            session.commit()

            job.status = "complete"
            job.output_minio_key = output_key
            job.output_media_id = media_item.id
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            session.refresh(job)

            is_retriable = isinstance(exc, TryoffModelClientError) or isinstance(
                exc, (ConnectionError, TimeoutError)
            )

            if is_retriable:
                if job.retry_count < job.max_retries:
                    delay = settings.TRYOFF_RETRY_BASE_DELAY_SECONDS * (
                        2 ** job.retry_count
                    )
                    job.retry_count += 1
                    job.status = "pending"
                    job.error_reason = str(exc)[:500]
                    session.commit()
                    self.retry(exc=exc, countdown=delay)
                else:
                    job.status = "failed"
                    job.error_reason = (
                        f"Failed after {job.max_retries} retries: {exc}"
                    )[:500]
                    job.completed_at = datetime.now(timezone.utc)
                    session.commit()
            else:
                job.status = "failed"
                job.error_reason = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
