from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.tryoff import (
    TryoffBatchRequest,
    TryoffBatchResponse,
    TryoffJobHistoryResponse,
    TryoffJobRequest,
    TryoffJobResponse,
    TryoffJobStatusResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.tryoff_job_repo import SourceImageRepo, TryoffJobRepo
from services.tryoff_job_service import (
    SourceImageNotFoundError,
    TryoffJobNotFoundError,
    TryoffJobOwnershipError,
    TryoffJobService,
)

router = APIRouter(prefix="/api/tryoff", tags=["tryoff"])


def _get_tryoff_service(db: AsyncSession = Depends(get_db)) -> TryoffJobService:
    tryoff_job_repo = TryoffJobRepo(db)
    source_image_repo = SourceImageRepo(db)
    minio_client = MinIOClient()
    return TryoffJobService(tryoff_job_repo, source_image_repo, minio_client)


@router.post(
    "/jobs",
    response_model=TryoffJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_tryoff_job(
    body: TryoffJobRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    tryoff_service: TryoffJobService = Depends(_get_tryoff_service),
):
    """Submit a new TryOff garment extraction job.

    Validates source image ownership, creates the job record, and queues
    a Celery task for async processing.
    """
    try:
        job = await tryoff_service.submit_job(
            mayorista_id=mayorista.id,
            source_image_id=body.source_image_id,
            garment_type=body.garment_type.value,
        )
    except SourceImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return TryoffJobResponse(
        job_id=job.id,
        status=job.status,
        garment_type=job.garment_type,
        created_at=job.created_at,
    )


@router.post(
    "/jobs/batch",
    response_model=TryoffBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_tryoff_batch(
    body: TryoffBatchRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    tryoff_service: TryoffJobService = Depends(_get_tryoff_service),
):
    """Submit multiple TryOff jobs for different garment types from the same source image.

    De-duplicates garment types and creates one job per unique type.
    """
    try:
        jobs = await tryoff_service.submit_batch(
            mayorista_id=mayorista.id,
            source_image_id=body.source_image_id,
            garment_types=[gt.value for gt in body.garment_types],
        )
    except SourceImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return TryoffBatchResponse(
        jobs=[
            TryoffJobResponse(
                job_id=job.id,
                status=job.status,
                garment_type=job.garment_type,
                created_at=job.created_at,
            )
            for job in jobs
        ]
    )


@router.get("/jobs/{job_id}", response_model=TryoffJobStatusResponse)
async def get_job_status(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    tryoff_service: TryoffJobService = Depends(_get_tryoff_service),
):
    """Get the current status of a TryOff job.

    Returns status info including a fresh presigned URL for the
    result image if the job is complete.
    """
    try:
        status_data = await tryoff_service.get_job_status(
            job_id=job_id,
            mayorista_id=mayorista.id,
        )
    except TryoffJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TryoffJobOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return TryoffJobStatusResponse(**status_data)


@router.get("/jobs", response_model=TryoffJobHistoryResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    tryoff_service: TryoffJobService = Depends(_get_tryoff_service),
):
    """List mayorista's TryOff jobs with pagination.

    Returns paginated job history ordered by creation date (newest first).
    Complete jobs include a fresh presigned URL for the result image.
    """
    items, total = await tryoff_service.list_jobs(
        mayorista_id=mayorista.id,
        page=page,
        page_size=page_size,
    )
    return TryoffJobHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
