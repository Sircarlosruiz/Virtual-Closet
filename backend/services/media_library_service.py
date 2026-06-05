import uuid

from core.minio_client import MinIOClient
from models.media import MediaItem
from repositories.media_repo import MediaItemRepo


class MediaLibraryService:
    """Handles media library operations for extracted garments and other media."""

    def __init__(self, media_item_repo: MediaItemRepo, minio_client: MinIOClient | None = None) -> None:
        self._media_item_repo = media_item_repo
        self._minio = minio_client or MinIOClient()

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

    async def list_extracted_garments(
        self,
        mayorista_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MediaItem], int]:
        """List extracted garments for a mayorista with pagination."""
        return await self._media_item_repo.list_by_type(
            mayorista_id, "extracted_garment", page, page_size
        )

    async def get_garment_by_id(
        self,
        garment_id: uuid.UUID,
        mayorista_id: uuid.UUID,
    ) -> MediaItem | None:
        """Get a single extracted garment by ID, enforcing ownership."""
        item = await self._media_item_repo.get_by_id(garment_id, mayorista_id)
        if item and item.media_type != "extracted_garment":
            return None
        return item

    async def get_presigned_url(self, minio_key: str) -> str:
        """Generate a presigned URL for a media item."""
        return await self._minio.get_presigned_url(
            bucket="originals", key=minio_key
        )

    async def save_vton_result(
        self,
        mayorista_id: uuid.UUID,
        minio_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        batch_id: uuid.UUID,
        batch_name: str,
        garment_id: uuid.UUID,
        model_id: uuid.UUID,
        vton_job_id: uuid.UUID,
    ) -> MediaItem:
        """Save a VTON result image to the media library with batch metadata.

        Args:
            mayorista_id: The owner of the media item.
            minio_key: The MinIO object key (result image).
            filename: Filename for the media item.
            content_type: MIME type (e.g., "image/jpeg").
            size_bytes: Size of the file in bytes.
            batch_id: The batch this result belongs to.
            batch_name: Human-readable batch name.
            garment_id: The garment used in the VTON job.
            model_id: The model used in the VTON job.
            vton_job_id: The VTON job that produced this result.

        Returns:
            The created MediaItem.
        """
        media_item = MediaItem(
            mayorista_id=mayorista_id,
            minio_key=minio_key,
            media_type="vton_result",
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            vton_job_id=vton_job_id,
            item_metadata={
                "type": "vton_result",
                "batch_id": str(batch_id),
                "batch_name": batch_name,
                "garment_id": str(garment_id),
                "model_id": str(model_id),
            },
        )
        return await self._media_item_repo.create(media_item)
