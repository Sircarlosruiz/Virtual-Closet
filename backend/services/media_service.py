import uuid

from core.minio_client import MinIOClient
from models.media import GarmentPhoto, ModelPhoto
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo


class InvalidFileTypeError(Exception):
    """Raised when the uploaded file is not JPG or PNG."""


class FileTooLargeError(Exception):
    """Raised when the uploaded file exceeds the 10MB limit."""


class EmptyFileError(Exception):
    """Raised when the uploaded file has zero bytes."""


class MediaNotFoundError(Exception):
    """Raised when a requested media entity is not found."""


# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


def _validate_file(data: bytes, content_type: str | None) -> None:
    """Validate file type and size using magic bytes."""
    if not data or len(data) == 0:
        raise EmptyFileError("File is empty")

    if len(data) > MAX_FILE_SIZE:
        raise FileTooLargeError("File size exceeds 10MB limit")

    # Validate via magic bytes (first bytes of file)
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Fallback: check magic bytes directly
        if len(data) >= 3:
            # PNG magic bytes: 89 50 4E 47
            png_signature = b"\x89PNG"
            # JPEG magic bytes: FF D8 FF
            jpeg_signature = b"\xff\xd8\xff"
            if not (
                data[:4] == png_signature or data[:3] == jpeg_signature
            ):
                raise InvalidFileTypeError("Only JPG and PNG files are accepted")
        else:
            raise InvalidFileTypeError("Only JPG and PNG files are accepted")


class MediaUploadService:
    """Handles garment and model photo uploads to MinIO."""

    def __init__(
        self,
        garment_repo: GarmentPhotoRepo,
        model_repo: ModelPhotoRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._garment_repo = garment_repo
        self._model_repo = model_repo
        self._minio = minio_client

    async def upload_garment(
        self,
        mayorista_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> tuple[GarmentPhoto, str]:
        """Upload a garment photo to MinIO and persist metadata.

        Returns:
            Tuple of (GarmentPhoto entity, presigned URL).
        """
        _validate_file(file_bytes, content_type)

        # Determine actual content type from magic bytes
        actual_content_type = content_type or "image/jpeg"
        if file_bytes[:4] == b"\x89PNG":
            actual_content_type = "image/png"
        elif file_bytes[:3] == b"\xff\xd8\xff":
            actual_content_type = "image/jpeg"

        ext = "png" if actual_content_type == "image/png" else "jpg"
        file_uuid = uuid.uuid4()
        minio_key = f"garments/{mayorista_id}/{file_uuid}.{ext}"

        await self._minio.upload_file(
            bucket="originals",
            key=minio_key,
            data=file_bytes,
            content_type=actual_content_type,
        )

        garment_photo = GarmentPhoto(
            id=file_uuid,
            mayorista_id=mayorista_id,
            minio_key=minio_key,
            filename=filename,
            content_type=actual_content_type,
            size_bytes=len(file_bytes),
        )
        garment_photo = await self._garment_repo.create(garment_photo)

        presigned_url = await self._minio.get_presigned_url(
            bucket="originals", key=minio_key
        )

        return garment_photo, presigned_url

    async def upload_model_photo(
        self,
        mayorista_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        label: str | None = None,
    ) -> tuple[ModelPhoto, str]:
        """Upload a model photo to MinIO and persist metadata.

        Returns:
            Tuple of (ModelPhoto entity, presigned URL).
        """
        _validate_file(file_bytes, content_type)

        actual_content_type = content_type or "image/jpeg"
        if file_bytes[:4] == b"\x89PNG":
            actual_content_type = "image/png"
        elif file_bytes[:3] == b"\xff\xd8\xff":
            actual_content_type = "image/jpeg"

        ext = "png" if actual_content_type == "image/png" else "jpg"
        file_uuid = uuid.uuid4()
        minio_key = f"models/{mayorista_id}/{file_uuid}.{ext}"

        await self._minio.upload_file(
            bucket="originals",
            key=minio_key,
            data=file_bytes,
            content_type=actual_content_type,
        )

        model_photo = ModelPhoto(
            id=file_uuid,
            mayorista_id=mayorista_id,
            minio_key=minio_key,
            label=label or filename,
            is_curated=False,
            content_type=actual_content_type,
            size_bytes=len(file_bytes),
        )
        model_photo = await self._model_repo.create(model_photo)

        presigned_url = await self._minio.get_presigned_url(
            bucket="originals", key=minio_key
        )

        return model_photo, presigned_url
