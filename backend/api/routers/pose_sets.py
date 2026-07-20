import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.pose_sets import (
    PoseSetCreateRequest,
    PoseSetCreateResponse,
    PoseSetDetailResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.batch_repo import BatchJobRepo
from repositories.media_repo import GarmentPhotoRepo, MediaItemRepo, ModelPhotoRepo
from repositories.model_repo import ModelRepo
from repositories.pose_set_repo import PoseSetRepo
from repositories.vton_job_repo import VTONJobRepo
from services.batch_submission_service import BatchSubmissionService
from services.media_library_service import MediaLibraryService
from services.pose_set_service import (
    DuplicatePoseSelectionError,
    EmptyPoseSelectionError,
    InvalidPoseSelectionError,
    PoseSetNotFoundError,
    PoseSetResultService,
    PoseSetSubmissionService,
)
from services.vton_job_service import VTONJobService

router = APIRouter(prefix="/api/pose-sets", tags=["pose-sets"])


def _get_services(db: AsyncSession):
    model_photo_repo = ModelPhotoRepo(db)
    garment_repo = GarmentPhotoRepo(db)
    batch_repo = BatchJobRepo(db)
    vton_service = VTONJobService(
        VTONJobRepo(db), garment_repo, model_photo_repo, None
    )
    batch_service = BatchSubmissionService(
        batch_repo, garment_repo, model_photo_repo, vton_service
    )
    pose_set_repo = PoseSetRepo(db)
    submission = PoseSetSubmissionService(
        pose_set_repo,
        ModelRepo(db),
        model_photo_repo,
        garment_repo,
        batch_repo,
        batch_service,
        db,
    )
    results = PoseSetResultService(
        pose_set_repo,
        batch_repo,
        model_photo_repo,
        MediaItemRepo(db),
        MediaLibraryService(MediaItemRepo(db), MinIOClient()),
    )
    return submission, results, batch_service


@router.post("", response_model=PoseSetCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_pose_set(
    payload: PoseSetCreateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    if mayorista.tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context is required")
    submission, _, batch_service = _get_services(db)
    try:
        pose_set, batch = await submission.submit(
            mayorista.id,
            mayorista.tenant_id,
            payload.garment_id,
            payload.model_id,
            payload.cloth_type,
            payload.pose_ids,
        )
        await db.commit()
        batch_service.publish_pending()
    except (EmptyPoseSelectionError, DuplicatePoseSelectionError, InvalidPoseSelectionError) as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Pose set submission failed") from exc
    return PoseSetCreateResponse(
        pose_set_id=pose_set.id, batch_id=batch.id, total_items=batch.total_items
    )


@router.get("/{pose_set_id}", response_model=PoseSetDetailResponse)
async def get_pose_set(
    pose_set_id: uuid.UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    _, results, _ = _get_services(db)
    try:
        return await results.get(mayorista.id, pose_set_id)
    except PoseSetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
