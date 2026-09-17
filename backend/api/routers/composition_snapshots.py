from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.composition_snapshot import CompositionSnapshotResponse
from api.schemas.image_generation import ImageGenerationResponse
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.generation_job_repo import GenerationJobRepository
from services.composition_snapshot_service import (
    CompositionSnapshotNotFoundError,
    CompositionSnapshotService,
    TemplateReferenceUnavailableError,
)
from services.image_generation_service import ImageGenerationService

router = APIRouter(prefix="/api/templates/snapshots", tags=["composition-snapshots"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def _get_service(db: AsyncSession = Depends(get_db)) -> CompositionSnapshotService:
    return CompositionSnapshotService(
        CompositionSnapshotRepository(db),
        ImageGenerationService(GenerationJobRepository(db)),
    )


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )


@router.get("/{generation_job_id}", response_model=CompositionSnapshotResponse)
async def get_composition_snapshot(
    generation_job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: CompositionSnapshotService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
) -> CompositionSnapshotResponse:
    _require_staff(mayorista)
    job = await GenerationJobRepository(db).get_owned(generation_job_id, mayorista.id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found"
        )

    try:
        snapshot = await service.get_snapshot(generation_job_id)
    except CompositionSnapshotNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return CompositionSnapshotResponse.model_validate(snapshot)


@router.post(
    "/{generation_job_id}/regenerate",
    response_model=ImageGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_from_snapshot(
    generation_job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: CompositionSnapshotService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
) -> ImageGenerationResponse:
    _require_staff(mayorista)
    job = await GenerationJobRepository(db).get_owned(generation_job_id, mayorista.id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found"
        )

    try:
        snapshot = await service.get_snapshot(generation_job_id)
    except CompositionSnapshotNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    try:
        new_job = await service.regenerate(job, snapshot)
    except TemplateReferenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    celery_app.send_task("tasks.generate_image", args=[str(new_job.id)])
    return ImageGenerationResponse(
        job_id=new_job.id,
        mode=new_job.mode,
        provider=new_job.provider,
        status=new_job.status,
        created_at=new_job.created_at,
    )
