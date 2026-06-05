import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.batch_job import BatchItem, BatchJob
from repositories.batch_repo import BatchJobRepo
from services.media_library_service import MediaLibraryService

logger = logging.getLogger(__name__)


class BatchMediaSaveService:
    """Handles saving VTON result images to the media library with batch metadata.

    Called from the completion callback after BatchItem status is updated.
    Uses idempotency check (result_media_id) + unique constraint (vton_job_id)
    to prevent duplicate media entries.
    """

    def __init__(
        self,
        batch_repo: BatchJobRepo,
        media_service: MediaLibraryService,
        db: AsyncSession,
    ) -> None:
        self._batch_repo = batch_repo
        self._media_service = media_service
        self._db = db

    async def save_result(
        self,
        batch_id: uuid.UUID,
        item_id: uuid.UUID,
        vton_job_id: uuid.UUID,
        result_minio_key: str,
    ) -> uuid.UUID | None:
        """Save result image to media library with batch metadata.

        Returns media_item_id on success, None on failure (graceful degradation).
        """
        # Fast-path idempotency check
        item = await self._batch_repo.get_item_by_id(item_id, batch_id)
        if item is None:
            logger.warning("BatchItem %s not found for media save", item_id)
            return None

        if item.result_media_id is not None:
            logger.info(
                "Media already saved for item %s (media_id: %s), skipping",
                item_id,
                item.result_media_id,
            )
            return item.result_media_id

        # Get batch for metadata
        batch = await self._batch_repo.get_by_id(batch_id)
        if batch is None:
            logger.error("Batch %s not found for media save", batch_id)
            return None

        try:
            media_item = await self._media_service.save_vton_result(
                mayorista_id=batch.mayorista_id,
                minio_key=result_minio_key,
                filename=f"batch_{batch.name}_{item.id}.jpg",
                content_type="image/jpeg",
                size_bytes=0,  # Unknown at save time
                batch_id=batch_id,
                batch_name=batch.name,
                garment_id=item.garment_id,
                model_id=item.model_id,
                vton_job_id=vton_job_id,
            )

            # Update item with media reference
            await self._batch_repo.set_result_media(item_id, media_item.id)
            await self._db.flush()

            logger.info(
                "Media saved for item %s (media_id: %s)",
                item_id,
                media_item.id,
            )
            return media_item.id

        except Exception as exc:
            # Check for unique constraint violation (duplicate callback)
            if "unique constraint" in str(exc).lower() or "duplicate" in str(exc).lower():
                logger.info(
                    "Duplicate media save for vton_job %s, skipping",
                    vton_job_id,
                )
                return None

            # Log error and flag for manual intervention
            logger.error(
                "Media save failed for item %s: %s",
                item_id,
                exc,
            )
            await self._batch_repo.set_media_save_error(item_id, str(exc)[:500])
            await self._db.flush()
            return None
