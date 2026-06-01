import uuid

from models.media import MediaItem
from repositories.media_repo import MediaItemRepo


class MediaLibraryService:
    """Handles media library operations for extracted garments and other media."""

    def __init__(self, media_item_repo: MediaItemRepo) -> None:
        self._media_item_repo = media_item_repo

    async def save_extracted_garment(
        self,
        mayorista_id: uuid.UUID,
        minio_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        garment_type: str,
        source_job_id: uuid.UUID,
        source_image_id: uuid.UUID,
    ) -> MediaItem:
        """Save an extracted garment to the media library.

        Creates a MediaItem with metadata for the extracted garment.

        Args:
            mayorista_id: The owner of the media item.
            minio_key: The MinIO object key.
            filename: The original filename.
            content_type: MIME type (e.g., "image/png").
            size_bytes: Size of the file in bytes.
            garment_type: Type of garment (upper, lower, dress).
            source_job_id: The TryoffJob that produced this garment.
            source_image_id: The source image used for extraction.

        Returns:
            The created MediaItem.
        """
        media_item = MediaItem(
            mayorista_id=mayorista_id,
            minio_key=minio_key,
            media_type="extracted_garment",
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            item_metadata={
                "type": "extracted_garment",
                "garment_type": garment_type,
                "source_job_id": str(source_job_id),
                "source_image_id": str(source_image_id),
            },
        )
        return await self._media_item_repo.create(media_item)
