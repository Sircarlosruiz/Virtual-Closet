import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from core.config import settings
from models.batch_job import BatchItem, BatchJob


def compute_batch_status(
    completed_count: int, failed_count: int, total_items: int
) -> str:
    """Pure function: compute BatchJob status from counters."""
    if completed_count + failed_count < total_items:
        return "in-progress"
    if completed_count == total_items:
        return "complete"
    if failed_count == total_items:
        return "failed"
    return "partial"


class BatchCompletionHandlerSync:
    """Synchronous version of BatchCompletionHandler for Celery workers.

    Uses sync SQLAlchemy connection (psycopg) instead of async (asyncpg).
    """

    def __init__(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        sync_url = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg://"
        )
        self._engine = create_engine(sync_url)
        self._Session = sessionmaker(self._engine)

    def on_vton_job_complete(
        self, vton_job_id: str, result_minio_key: str
    ) -> None:
        """Handle successful VtonJob completion (sync version)."""
        with self._Session() as session:
            # Find the BatchItem linked to this VtonJob
            stmt = (
                select(BatchItem)
                .where(BatchItem.vton_job_id == uuid.UUID(vton_job_id))
                .with_for_update()
            )
            result = session.execute(stmt)
            item = result.scalar_one_or_none()

            if item is None:
                return  # Not a batch job

            # Update item status
            item.status = "complete"
            item.completed_at = datetime.now(timezone.utc)

            # Atomic counter increment
            counter_stmt = (
                update(BatchJob)
                .where(BatchJob.id == item.batch_id)
                .values(
                    completed_count=BatchJob.completed_count + 1,
                )
                .returning(
                    BatchJob.completed_count,
                    BatchJob.failed_count,
                    BatchJob.total_items,
                    BatchJob.status,
                )
            )
            counter_result = session.execute(counter_stmt)
            row = counter_result.first()

            new_status = compute_batch_status(
                row.completed_count, row.failed_count, row.total_items
            )

            if row.status != new_status:
                status_update = (
                    update(BatchJob)
                    .where(BatchJob.id == item.batch_id)
                    .values(
                        status=new_status,
                        completed_at=(
                            datetime.now(timezone.utc)
                            if new_status in ("complete", "partial", "failed")
                            else None
                        ),
                    )
                )
                session.execute(status_update)

            session.commit()

    def on_vton_job_failed(
        self, vton_job_id: str, error_message: str
    ) -> None:
        """Handle permanent VtonJob failure (sync version)."""
        with self._Session() as session:
            stmt = (
                select(BatchItem)
                .where(BatchItem.vton_job_id == uuid.UUID(vton_job_id))
                .with_for_update()
            )
            result = session.execute(stmt)
            item = result.scalar_one_or_none()

            if item is None:
                return  # Not a batch job

            # Update item status
            item.status = "failed"
            item.error_message = error_message[:500]
            item.completed_at = datetime.now(timezone.utc)

            # Atomic counter increment
            counter_stmt = (
                update(BatchJob)
                .where(BatchJob.id == item.batch_id)
                .values(
                    failed_count=BatchJob.failed_count + 1,
                )
                .returning(
                    BatchJob.completed_count,
                    BatchJob.failed_count,
                    BatchJob.total_items,
                    BatchJob.status,
                )
            )
            counter_result = session.execute(counter_stmt)
            row = counter_result.first()

            new_status = compute_batch_status(
                row.completed_count, row.failed_count, row.total_items
            )

            if row.status != new_status:
                status_update = (
                    update(BatchJob)
                    .where(BatchJob.id == item.batch_id)
                    .values(
                        status=new_status,
                        completed_at=(
                            datetime.now(timezone.utc)
                            if new_status in ("complete", "partial", "failed")
                            else None
                        ),
                    )
                )
                session.execute(status_update)

            session.commit()
