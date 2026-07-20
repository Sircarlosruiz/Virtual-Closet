import uuid

from sqlalchemy.exc import IntegrityError

from core.minio_client import MinIOClient
from models.media import ModelPhoto
from models.model import Model
from repositories.media_repo import ModelPhotoRepo
from repositories.model_repo import ModelRepo
from services.media_service import MediaUploadService

VALID_POSES = ("front", "side", "back")


class ModelNotFoundError(Exception):
    """Raised when the target model does not exist or is not owned (ADR-013)."""


class DuplicatePoseError(Exception):
    """Raised when the pose type is already used on the model."""


class InvalidPoseError(Exception):
    """Raised when the pose value is outside the fixed enum."""


class ModelPoseService:
    """Business logic for Model aggregates and their pose photos."""

    def __init__(
        self,
        model_repo: ModelRepo,
        model_photo_repo: ModelPhotoRepo,
        upload_service: MediaUploadService,
        minio_client: MinIOClient,
    ) -> None:
        self._model_repo = model_repo
        self._model_photo_repo = model_photo_repo
        self._upload_service = upload_service
        self._minio = minio_client

    async def create_model(self, mayorista_id: uuid.UUID, name: str) -> Model:
        """Create a new Model identity for the mayorista."""
        model = Model(mayorista_id=mayorista_id, name=name)
        return await self._model_repo.create(model)

    async def list_models(self, mayorista_id: uuid.UUID) -> list[tuple[Model, int]]:
        """List owned model identities with their current pose counts."""
        models = await self._model_repo.list_by_mayorista(mayorista_id)
        results = []
        for model in models:
            photos = await self._model_photo_repo.list_by_model(model.id)
            results.append((model, len(photos)))
        return results

    async def upload_pose(
        self,
        mayorista_id: uuid.UUID,
        model_id: uuid.UUID,
        pose: str,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> tuple[ModelPhoto, str]:
        """Upload a pose photo for a model.

        Raises:
            ModelNotFoundError: model missing or owned by another mayorista.
            InvalidPoseError: pose outside the fixed enum.
            DuplicatePoseError: pose type already present on the model.
        """
        model = await self._model_repo.get_by_id(model_id, mayorista_id)
        if model is None:
            raise ModelNotFoundError("Model not found")

        if pose not in VALID_POSES:
            raise InvalidPoseError(
                f"Invalid pose type: {pose}. Must be one of {VALID_POSES}"
            )

        # Fast-path check (ADR-010); the DB unique constraint is authoritative.
        if await self._model_photo_repo.pose_exists(model_id, pose):
            raise DuplicatePoseError("Pose type already exists for this model")

        try:
            return await self._upload_service.upload_model_photo(
                mayorista_id=mayorista_id,
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                label=f"{model.name} - {pose}",
                model_id=model_id,
                pose=pose,
            )
        except IntegrityError as exc:
            # Concurrent upload of the same pose type won the race.
            raise DuplicatePoseError(
                "Pose type already exists for this model"
            ) from exc

    async def list_poses(
        self, mayorista_id: uuid.UUID, model_id: uuid.UUID
    ) -> list[tuple[ModelPhoto, str]]:
        """List a model's pose photos with presigned URLs, ordered front/side/back.

        Raises:
            ModelNotFoundError: model missing or owned by another mayorista.
        """
        model = await self._model_repo.get_by_id(model_id, mayorista_id)
        if model is None:
            raise ModelNotFoundError("Model not found")

        photos = await self._model_photo_repo.list_by_model(model_id)
        results = []
        for photo in photos:
            presigned_url = await self._minio.get_presigned_url(
                bucket="originals", key=photo.minio_key
            )
            results.append((photo, presigned_url))
        return results
