from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.models import (
    ModelCreateRequest,
    ModelListItemResponse,
    ModelListResponse,
    ModelResponse,
    PoseListResponse,
    PosePhotoResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from repositories.model_repo import ModelRepo
from services.media_service import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFileTypeError,
    MediaUploadService,
)
from services.model_pose_service import (
    DuplicatePoseError,
    InvalidPoseError,
    ModelNotFoundError,
    ModelPoseService,
)

router = APIRouter(prefix="/api/models", tags=["models"])


def _get_model_pose_service(db: AsyncSession = Depends(get_db)) -> ModelPoseService:
    model_photo_repo = ModelPhotoRepo(db)
    minio_client = MinIOClient()
    upload_service = MediaUploadService(
        GarmentPhotoRepo(db), model_photo_repo, minio_client
    )
    return ModelPoseService(
        ModelRepo(db), model_photo_repo, upload_service, minio_client
    )


@router.post(
    "",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    payload: ModelCreateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModelPoseService = Depends(_get_model_pose_service),
):
    """Create a named Model identity for the authenticated mayorista."""
    model = await service.create_model(mayorista_id=mayorista.id, name=payload.name)
    return ModelResponse.model_validate(model)


@router.get("", response_model=ModelListResponse)
async def list_models(
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModelPoseService = Depends(_get_model_pose_service),
):
    """List named Models owned by the authenticated mayorista."""
    models = await service.list_models(mayorista.id)
    return ModelListResponse(
        items=[
            ModelListItemResponse(
                id=model.id,
                mayorista_id=model.mayorista_id,
                name=model.name,
                created_at=model.created_at,
                pose_count=pose_count,
            )
            for model, pose_count in models
        ],
        total=len(models),
    )


@router.post(
    "/{model_id}/poses",
    response_model=PosePhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pose_photo(
    model_id: UUID,
    file: UploadFile = File(...),
    pose: str = Form(...),
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModelPoseService = Depends(_get_model_pose_service),
):
    """Upload a pose photo (front/side/back, JPG/PNG max 10MB) for a model."""
    file_bytes = await file.read()

    try:
        photo, presigned_url = await service.upload_pose(
            mayorista_id=mayorista.id,
            model_id=model_id,
            pose=pose,
            file_bytes=file_bytes,
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidPoseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DuplicatePoseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except (EmptyFileError, FileTooLargeError, InvalidFileTypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PosePhotoResponse(
        id=photo.id,
        model_id=photo.model_id,
        pose=photo.pose,
        presigned_url=presigned_url,
        uploaded_at=photo.uploaded_at,
    )


@router.get("/{model_id}/poses", response_model=PoseListResponse)
async def list_model_poses(
    model_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ModelPoseService = Depends(_get_model_pose_service),
):
    """List pose photos for a model, ordered front, side, back (ADR-013: 404 if unowned)."""
    try:
        items = await service.list_poses(
            mayorista_id=mayorista.id, model_id=model_id
        )
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return PoseListResponse(
        items=[
            PosePhotoResponse(
                id=photo.id,
                model_id=photo.model_id,
                pose=photo.pose,
                presigned_url=presigned_url,
                uploaded_at=photo.uploaded_at,
            )
            for photo, presigned_url in items
        ],
        total=len(items),
    )
