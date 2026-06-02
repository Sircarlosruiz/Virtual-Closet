import uuid

from core.minio_client import MinIOClient
from models.tryoff_job import SourceImage
from repositories.tryoff_job_repo import SourceImageRepo
from services.media_service import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileTypeError,
    _validate_file,
)


class TryoffSourceImageService:
    """Uploads TryOff source images to MinIO and persists tryoff_source_images rows."""

    def __init__(
        self,
        source_image_repo: SourceImageRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._source_image_repo = source_image_repo
        self._minio = minio_client

    async def upload(
        self,
        mayorista_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> tuple[SourceImage, str]:
        _validate_file(file_bytes, content_type)

        actual_content_type = content_type or "image/jpeg"
        if file_bytes[:4] == b"\x89PNG":
            actual_content_type = "image/png"
        elif file_bytes[:3] == b"\xff\xd8\xff":
            actual_content_type = "image/jpeg"

        ext = "png" if actual_content_type == "image/png" else "jpg"
        image_id = uuid.uuid4()
        minio_key = f"tryoff/source/{mayorista_id}/{image_id}.{ext}"

        await self._minio.upload_file(
            bucket="originals",
            key=minio_key,
            data=file_bytes,
            content_type=actual_content_type,
        )

        source_image = SourceImage(
            id=image_id,
            mayorista_id=mayorista_id,
            minio_key=minio_key,
            filename=filename,
            content_type=actual_content_type,
            size_bytes=len(file_bytes),
        )
        source_image = await self._source_image_repo.create(source_image)

        presigned_url = await self._minio.get_presigned_url(
            bucket="originals", key=minio_key
        )
        return source_image, presigned_url


__all__ = [
    "TryoffSourceImageService",
    "EmptyFileError",
    "FileTooLargeError",
    "InvalidFileTypeError",
]
