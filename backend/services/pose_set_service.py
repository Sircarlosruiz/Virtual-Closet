import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.batches import BatchCreateRequest, BatchItemCreateRequest
from models.batch_job import BatchJob
from models.media import MediaItem
from models.pose_set import PoseSet
from repositories.batch_repo import BatchJobRepo
from repositories.media_repo import GarmentPhotoRepo, MediaItemRepo, ModelPhotoRepo
from repositories.model_repo import ModelRepo
from repositories.pose_set_repo import PoseSetRepo
from services.batch_submission_service import BatchSubmissionService
from services.media_library_service import MediaLibraryService


class EmptyPoseSelectionError(Exception):
    """Raised when no poses were selected."""


class DuplicatePoseSelectionError(Exception):
    """Raised when a pose ID is submitted more than once."""


class InvalidPoseSelectionError(Exception):
    """Raised when a pose ID is not part of the selected Model."""


class PoseSetNotFoundError(Exception):
    """Raised when a PoseSet is missing or unowned."""


class PoseSetSubmissionService:
    """Coordinates PoseSet validation with the existing batch service."""

    def __init__(
        self,
        pose_set_repo: PoseSetRepo,
        model_repo: ModelRepo,
        model_photo_repo: ModelPhotoRepo,
        garment_repo: GarmentPhotoRepo,
        batch_repo: BatchJobRepo,
        batch_service: BatchSubmissionService,
        db: AsyncSession,
    ) -> None:
        self._pose_set_repo = pose_set_repo
        self._model_repo = model_repo
        self._model_photo_repo = model_photo_repo
        self._garment_repo = garment_repo
        self._batch_repo = batch_repo
        self._batch_service = batch_service
        self._db = db

    async def submit(
        self,
        mayorista_id: uuid.UUID,
        tenant_id: uuid.UUID,
        garment_id: uuid.UUID,
        model_id: uuid.UUID,
        cloth_type: str,
        pose_ids: list[uuid.UUID],
    ) -> tuple[PoseSet, BatchJob]:
        if not pose_ids:
            raise EmptyPoseSelectionError("At least one pose must be selected")
        if len(set(pose_ids)) != len(pose_ids):
            raise DuplicatePoseSelectionError("Duplicate poses are not allowed")

        model = await self._model_repo.get_by_id(model_id, mayorista_id)
        garment = await self._garment_repo.get_by_id(garment_id, mayorista_id)
        if model is None or garment is None:
            raise InvalidPoseSelectionError("Model or garment is not owned by you")

        photos = await self._model_photo_repo.list_by_ids_for_model(
            pose_ids, model_id, mayorista_id
        )
        if len(photos) != len(pose_ids):
            raise InvalidPoseSelectionError(
                "All poses must belong to the selected model"
            )

        request = BatchCreateRequest(
            name=f"Pose set - {model.name}",
            items=[
                BatchItemCreateRequest(
                    garment_id=garment_id,
                    model_id=photo.id,
                    cloth_type=cloth_type,
                )
                for photo in photos
            ],
        )
        batch = await self._batch_service.create_and_submit(
            mayorista_id=mayorista_id,
            request=request,
            db=self._db,
            tenant_id=tenant_id,
        )
        pose_set = PoseSet(
            mayorista_id=mayorista_id,
            tenant_id=tenant_id,
            model_id=model_id,
            garment_id=garment_id,
            batch_id=batch.id,
        )
        await self._pose_set_repo.create(pose_set)
        return pose_set, batch


class PoseSetResultService:
    """Projects grouped PoseSet results from existing batch state."""

    def __init__(
        self,
        pose_set_repo: PoseSetRepo,
        batch_repo: BatchJobRepo,
        model_photo_repo: ModelPhotoRepo,
        media_repo: MediaItemRepo,
        media_service: MediaLibraryService,
    ) -> None:
        self._pose_set_repo = pose_set_repo
        self._batch_repo = batch_repo
        self._model_photo_repo = model_photo_repo
        self._media_repo = media_repo
        self._media_service = media_service

    async def get(self, mayorista_id: uuid.UUID, pose_set_id: uuid.UUID) -> dict:
        pose_set = await self._pose_set_repo.get_by_id_and_mayorista(
            pose_set_id, mayorista_id
        )
        if pose_set is None:
            raise PoseSetNotFoundError("Pose set not found")

        batch = await self._batch_repo.get_by_id_and_mayorista(
            pose_set.batch_id, mayorista_id
        )
        if batch is None:
            raise PoseSetNotFoundError("Pose set not found")

        photos = await self._model_photo_repo.list_by_ids_for_model(
            [item.model_id for item in batch.items], pose_set.model_id, mayorista_id
        )
        photo_by_id = {photo.id: photo for photo in photos}
        items = []
        for item in batch.items:
            photo = photo_by_id.get(item.model_id)
            media: MediaItem | None = None
            image_url: str | None = None
            if item.result_media_id is not None:
                media = await self._media_repo.get_by_id(
                    item.result_media_id, mayorista_id
                )
                if media is not None:
                    image_url = await self._media_service.get_presigned_url(
                        media.minio_key
                    )
            items.append(
                {
                    "pose_type": photo.pose if photo else None,
                    "batch_item_id": item.id,
                    "media_id": media.id if media else None,
                    "image_url": image_url,
                    "status": item.status,
                    "error_message": item.error_message,
                }
            )

        statuses = [item["status"] for item in items]
        if statuses and all(status == "complete" for status in statuses):
            status = "complete"
        elif statuses and all(status == "failed" for status in statuses):
            status = "failed"
        elif len(set(statuses)) > 1:
            status = "partial"
        else:
            status = batch.status

        return {
            "pose_set_id": pose_set.id,
            "batch_id": pose_set.batch_id,
            "garment_id": pose_set.garment_id,
            "model_id": pose_set.model_id,
            "status": status,
            "items": items,
        }
