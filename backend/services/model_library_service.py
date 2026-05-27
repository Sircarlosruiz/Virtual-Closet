import uuid

from core.minio_client import MinIOClient
from models.media import ModelPhoto
from repositories.media_repo import ModelPhotoRepo


class ModelLibraryService:
    """Handles curated model library and own model photo listing."""

    def __init__(
        self,
        model_repo: ModelPhotoRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._model_repo = model_repo
        self._minio = minio_client

    async def list_curated_models(self) -> list[tuple[ModelPhoto, str]]:
        """List all curated model photos with presigned URLs.

        Returns:
            List of (ModelPhoto, presigned_url) tuples.
        """
        models = await self._model_repo.list_curated()
        results = []
        for model in models:
            presigned_url = await self._minio.get_presigned_url(
                bucket="originals", key=model.minio_key
            )
            results.append((model, presigned_url))
        return results

    async def list_own_models(
        self, mayorista_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[tuple[ModelPhoto, str]], int]:
        """List mayorista's own uploaded model photos with presigned URLs.

        Returns:
            Tuple of (list of (ModelPhoto, presigned_url), total count).
        """
        models, total = await self._model_repo.list_by_mayorista(
            mayorista_id, page, page_size
        )
        results = []
        for model in models:
            presigned_url = await self._minio.get_presigned_url(
                bucket="originals", key=model.minio_key
            )
            results.append((model, presigned_url))
        return results, total

    async def get_presigned_url(self, minio_key: str) -> str:
        """Generate a presigned URL for any stored model photo."""
        return await self._minio.get_presigned_url(
            bucket="originals", key=minio_key
        )
