import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.batch_job import BatchItem, BatchJob
from services.batch_media_save_service import BatchMediaSaveService

logger = logging.getLogger(__name__)


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


class BatchCompletionHandler:
    """Handles VtonJob completion/failure callbacks for batch items.

    Called from the Celery task after VtonJob status is updated.
    Uses atomic counter updates (F() expressions) to prevent lost updates
    under concurrent Celery workers.
    """

    def __init__(
        self,
        db: AsyncSession,
        media_save_service: BatchMediaSaveService | None = None,
    ) -> None:
        self._db = db
        self._media_save_service = media_save_service

    async def on_vton_job_complete(
        self, vton_job_id: uuid.UUID, result_minio_key: str
    ) -> None:
        """Handle successful VtonJob completion.

        1. Look up BatchItem via VtonJob.batch_item_id
        2. Update BatchItem status → complete
        3. Atomically increment BatchJob.completed_count
        4. Recompute BatchJob status; set completed_at if terminal
        """
        # Find the BatchItem linked to this VtonJob
        stmt = (
            select(BatchItem)
            .where(BatchItem.vton_job_id == vton_job_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        item = result.scalar_one_or_none()

        if item is None:
            # Not a batch job — nothing to do
            return

        # Update item status
        item.status = "complete"
        item.completed_at = datetime.now(timezone.utc)

        # Atomic counter increment + status computation
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
        counter_result = await self._db.execute(counter_stmt)
        row = counter_result.first()

        new_status = compute_batch_status(
            row.completed_count, row.failed_count, row.total_items
        )

        # Update batch status if changed
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
            await self._db.execute(status_update)

        # Media save (graceful degradation)
        if self._media_save_service:
            try:
                await self._media_save_service.save_result(
                    batch_id=item.batch_id,
                    item_id=item.id,
                    vton_job_id=vton_job_id,
                    result_minio_key=result_minio_key,
                )
            except Exception:
                logger.warning(
                    "Media save failed for item %s (graceful degradation)",
                    item.id,
                )

        logger.info(
            "Batch item %s completed (batch %s, status %s)",
            item.id,
            item.batch_id,
            new_status,
        )

    async def on_vton_job_failed(
        self, vton_job_id: uuid.UUID, error_message: str
    ) -> None:
        """Handle permanent VtonJob failure.

        1. Look up BatchItem via VtonJob.batch_item_id
        2. Update BatchItem status → failed with error message
        3. Atomically increment BatchJob.failed_count
        4. Recompute BatchJob status; set completed_at if terminal
        """
        stmt = (
            select(BatchItem)
            .where(BatchItem.vton_job_id == vton_job_id)
            .with_for_update()
        )
        result = await self._db.execute(stmt)
        item = result.scalar_one_or_none()

        if item is None:
            # Not a batch job — nothing to do
            return

        # Update item status
        item.status = "failed"
        item.error_message = error_message[:500]
        item.completed_at = datetime.now(timezone.utc)

        # Atomic counter increment + status computation
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
        counter_result = await self._db.execute(counter_stmt)
        row = counter_result.first()

        new_status = compute_batch_status(
            row.completed_count, row.failed_count, row.total_items
        )

        # Update batch status if changed
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
            await self._db.execute(status_update)

        logger.warning(
            "Batch item %s failed (batch %s, status %s, error: %s)",
            item.id,
            item.batch_id,
            new_status,
            error_message[:100],
        )
