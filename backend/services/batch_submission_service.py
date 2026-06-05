import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.batches import BatchCreateRequest
from models.batch_job import BATCH_ITEM_CAP, BatchItem, BatchJob, BatchJobStatus
from repositories.batch_repo import BatchJobRepo
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from services.vton_job_service import VTONJobService

logger = logging.getLogger(__name__)


class BatchSizeExceededError(Exception):
    """Raised when batch items exceed the maximum cap."""


class EmptyBatchError(Exception):
    """Raised when batch has no items."""


class MayoristaOwnershipError(Exception):
    """Raised when a garment/model doesn't belong to the mayorista."""


class BatchSubmissionError(Exception):
    """Raised when batch submission fails after partial work."""


class BatchSubmissionService:
    """Handles atomic batch creation and VTON job enqueueing."""

    def __init__(
        self,
        batch_repo: BatchJobRepo,
        garment_repo: GarmentPhotoRepo,
        model_repo: ModelPhotoRepo,
        vton_job_service: VTONJobService,
    ) -> None:
        self._batch_repo = batch_repo
        self._garment_repo = garment_repo
        self._model_repo = model_repo
        self._vton_service = vton_job_service

    async def create_and_submit(
        self,
        mayorista_id: uuid.UUID,
        request: BatchCreateRequest,
        db: AsyncSession,
    ) -> BatchJob:
        """Create a BatchJob with items and enqueue VTON jobs atomically.

        Validates ownership of all garments/models, creates BatchJob +
        BatchItem records, and enqueues each item as a VtonJob within
        a single database transaction.

        Raises:
            EmptyBatchError: If items list is empty.
            BatchSizeExceededError: If items exceed BATCH_ITEM_CAP.
            MayoristaOwnershipError: If any garment doesn't belong to mayorista.
            BatchSubmissionError: If enqueueing fails during transaction.
        """
        items_count = len(request.items)
        if items_count == 0:
            raise EmptyBatchError("Batch must contain at least 1 item")
        if items_count > BATCH_ITEM_CAP:
            raise BatchSizeExceededError(
                f"Batch size exceeds maximum of {BATCH_ITEM_CAP} items"
            )

        # Validate ownership of all garments and existence of all models
        await self._verify_ownership(mayorista_id, request.items)

        # Generate batch name if not provided
        batch_name = request.name or f"Batch {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

        # Create BatchJob
        batch = BatchJob(
            mayorista_id=mayorista_id,
            name=batch_name,
            status=BatchJobStatus.pending.value,
            total_items=items_count,
        )

        # Create BatchItem records
        batch_items = [
            BatchItem(
                batch_id=batch.id,  # Will be set after flush
                garment_id=item.garment_id,
                model_id=item.model_id,
                cloth_type=item.cloth_type,
                status="pending",
            )
            for item in request.items
        ]

        # Atomic creation
        await self._batch_repo.create_with_items(batch, batch_items)
        await db.flush()  # Get IDs

        # Enqueue VtonJobs for each item (within same transaction)
        for batch_item in batch_items:
            try:
                vton_job = await self._vton_service.submit_job(
                    mayorista_id=mayorista_id,
                    garment_photo_id=batch_item.garment_id,
                    model_photo_id=batch_item.model_id,
                    cloth_type=batch_item.cloth_type,
                )
                batch_item.vton_job_id = vton_job.id
                batch_item.status = "processing"
            except Exception as exc:
                logger.error(
                    "Failed to enqueue VtonJob for batch item %s: %s",
                    batch_item.id,
                    exc,
                )
                raise BatchSubmissionError(
                    f"Failed to enqueue item: {exc}"
                ) from exc

        # Update batch status to in-progress
        batch.status = BatchJobStatus.in_progress.value

        await db.flush()
        return batch

    async def _verify_ownership(
        self,
        mayorista_id: uuid.UUID,
        items: list,
    ) -> None:
        """Verify all garments belong to mayorista and all models exist."""
        for item in items:
            # Verify garment ownership
            garment = await self._garment_repo.get_by_id_and_mayorista(
                item.garment_id, mayorista_id
            )
            if garment is None:
                exists = await self._garment_repo.get_by_id(item.garment_id)
                if exists is None:
                    raise MayoristaOwnershipError(
                        f"Garment {item.garment_id} not found"
                    )
                raise MayoristaOwnershipError(
                    f"Garment {item.garment_id} does not belong to you"
                )

            # Verify model existence (can be curated or owned)
            model = await self._model_repo.get_by_id(item.model_id)
            if model is None:
                raise MayoristaOwnershipError(
                    f"Model {item.model_id} not found"
                )
            if not model.is_curated and model.mayorista_id != mayorista_id:
                raise MayoristaOwnershipError(
                    f"Model {item.model_id} does not belong to you"
                )
