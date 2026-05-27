from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.vton import (
    VTONGenerateRequest,
    VTONJobCreateResponse,
    VTONJobStatusResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.media_repo import GarmentPhotoRepo, ModelPhotoRepo
from repositories.vton_job_repo import VTONJobRepo
from services.vton_job_service import (
    PhotoNotFoundError,
    PhotoOwnershipError,
    VTONJobService,
)

router = APIRouter(prefix="/api/vton", tags=["vton"])


def _get_vton_service(db: AsyncSession = Depends(get_db)) -> VTONJobService:
    vton_job_repo = VTONJobRepo(db)
    garment_repo = GarmentPhotoRepo(db)
    model_repo = ModelPhotoRepo(db)
    minio_client = MinIOClient()
    return VTONJobService(vton_job_repo, garment_repo, model_repo, minio_client)


@router.post(
    "/generate",
    response_model=VTONJobCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_vton_job(
    body: VTONGenerateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    vton_service: VTONJobService = Depends(_get_vton_service),
):
    """Submit a new VTON generation job.

    Validates photo ownership, creates the job record, and queues
    a Celery task for async processing.
    """
    try:
        job, _ = await vton_service.submit_job(
            mayorista_id=mayorista.id,
            garment_photo_id=body.garment_photo_id,
            model_photo_id=body.model_photo_id,
            cloth_type=body.cloth_type.value,
        )
    except PhotoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PhotoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return VTONJobCreateResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}", response_model=VTONJobStatusResponse)
async def get_job_status(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    vton_service: VTONJobService = Depends(_get_vton_service),
):
    """Get the current status of a VTON job.

    Returns status info including a fresh presigned URL for the
    result image if the job is completed.
    """
    try:
        status_data = await vton_service.get_job_status(
            job_id=job_id,
            mayorista_id=mayorista.id,
        )
    except PhotoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PhotoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return VTONJobStatusResponse(**status_data)
