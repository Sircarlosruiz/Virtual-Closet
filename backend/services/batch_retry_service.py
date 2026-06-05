import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.batch_job import BatchItem, BatchJob
from repositories.batch_repo import BatchJobRepo
from services.batch_completion_handler import compute_batch_status
from services.vton_job_service import VTONJobService

logger = logging.getLogger(__name__)


class ItemNotFailedError(Exception):
    """Raised when retry is attempted on a non-failed item."""


class MayoristaOwnershipError(Exception):
    """Raised when batch doesn't belong to the requesting mayorista."""


class RetryEnqueueError(Exception):
    """Raised when retry enqueue fails."""


class BatchRetryService:
    """Handles retry of failed batch items.

    Creates a new VtonJob for the failed item, resets item status,
    and updates batch counters.
    """

    def __init__(
        self,
        batch_repo: BatchJobRepo,
        vton_job_service: VTONJobService,
        db: AsyncSession,
    ) -> None:
        self._batch_repo = batch_repo
        self._vton_service = vton_job_service
        self._db = db

    async def retry_item(
        self,
        batch_id: uuid.UUID,
        item_id: uuid.UUID,
        mayorista_id: uuid.UUID,
    ) -> BatchItem:
        """Retry a failed batch item.

        1. Verify batch belongs to mayorista
        2. Verify item is in failed status
        3. Create new VtonJob for the same pairing
        4. Reset item status to pending, set new vton_job_id
        5. Decrement failed_count, re-evaluate batch status

        Raises:
            MayoristaOwnershipError: If batch doesn't belong to mayorista.
            ItemNotFailedError: If item is not in failed status.
            RetryEnqueueError: If VtonJob creation fails.
        """
        # Verify batch ownership
        batch = await self._batch_repo.get_by_id_and_mayorista(
            batch_id, mayorista_id
        )
        if batch is None:
            exists = await self._batch_repo.get_by_id(batch_id)
            if exists is None:
                raise MayoristaOwnershipError("Batch not found")
            raise MayoristaOwnershipError("You do not own this batch")

        # Verify item exists and is failed
        item = await self._batch_repo.get_item_by_id(item_id, batch_id)
        if item is None:
            raise MayoristaOwnershipError("Batch item not found")

        if item.status != "failed":
            raise ItemNotFailedError(
                f"Can only retry failed items (current status: {item.status})"
            )

        # Create new VtonJob for the same pairing
        try:
            vton_job, _ = await self._vton_service.submit_job(
                mayorista_id=mayorista_id,
                garment_photo_id=item.garment_id,
                model_photo_id=item.model_id,
                cloth_type=item.cloth_type,
            )
        except Exception as exc:
            logger.error("Failed to enqueue retry for item %s: %s", item_id, exc)
            raise RetryEnqueueError(f"Failed to enqueue retry: {exc}") from exc

        # Reset item status and link to new VtonJob
        item.status = "pending"
        item.vton_job_id = vton_job.id
        item.error_message = None
        item.completed_at = None
        item.retry_count = getattr(item, "retry_count", 0) + 1

        # Decrement failed_count and re-evaluate batch status
        counter_stmt = (
            update(BatchJob)
            .where(BatchJob.id == batch_id)
            .values(
                failed_count=BatchJob.failed_count - 1,
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

        # If batch was terminal, it's now back in progress
        if row.status != new_status:
            status_update = (
                update(BatchJob)
                .where(BatchJob.id == batch_id)
                .values(
                    status=new_status,
                    completed_at=None,  # Clear completed_at when recovering
                )
            )
            await self._db.execute(status_update)

        await self._db.flush()
        return item
