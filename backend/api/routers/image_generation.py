from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.image_generation import (
    ImageGenerationDetailResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ProviderAttemptSummary,
    UsageSummary,
)
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.generation_job_repo import GenerationJobRepository
from repositories.provider_invocation_repo import ProviderInvocationRepository
from services.idempotency_service import IdempotencyConflictError
from services.image_generation_service import ImageGenerationService
from services.publication_service import preview_object_url

router = APIRouter(prefix="/api/image-generation", tags=["image-generation"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def _get_service(db: AsyncSession = Depends(get_db)) -> ImageGenerationService:
    return ImageGenerationService(GenerationJobRepository(db))


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")


def _response(job) -> ImageGenerationResponse:
    return ImageGenerationResponse(
        job_id=job.id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
    )


def _detail_response(job, invocations, preview_url: str | None = None) -> ImageGenerationDetailResponse:
    return ImageGenerationDetailResponse(
        job_id=job.id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
        attempts=[
            ProviderAttemptSummary(
                attempt_number=inv.attempt_number,
                status=inv.status,
                error_code=inv.error_code,
                started_at=inv.started_at,
                completed_at=inv.completed_at,
            )
            for inv in invocations
        ],
        usage=UsageSummary(
            status=job.usage_status, model=job.usage_model, call_count=job.usage_call_count
        ),
        preview_url=preview_url,
        queue_wait_seconds=job.queue_wait_seconds,
        execution_seconds=job.execution_seconds,
    )


@router.post("/jobs", response_model=ImageGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_image_generation_job(
    body: ImageGenerationRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ImageGenerationService = Depends(_get_service),
) -> ImageGenerationResponse:
    _require_staff(mayorista)

    try:
        job, created = await service.create_job(mayorista.id, body, idempotency_key)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if created:
        celery_app.send_task("tasks.generate_image", args=[str(job.id)])
    return _response(job)


@router.get("/jobs/{job_id}", response_model=ImageGenerationDetailResponse)
async def get_image_generation_job(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ImageGenerationService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
) -> ImageGenerationDetailResponse:
    job = await service.get_job(job_id, mayorista.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    invocations = await ProviderInvocationRepository(db).list_by_job(job_id)
    preview_url = await preview_object_url(job.result_key)
    return _detail_response(job, invocations, preview_url)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ImageGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_image_generation_job(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
) -> ImageGenerationResponse:
    _require_staff(mayorista)

    job_repo = GenerationJobRepository(db)
    job = await job_repo.get_owned(job_id, mayorista.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")

    invocations = await ProviderInvocationRepository(db).list_by_job(job_id)
    latest = invocations[-1] if invocations else None
    if job.status != "failed" or latest is None or latest.error_category != "transient":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is not in a retryable state",
        )

    job = await job_repo.update_status(job_id, status="queued")
    celery_app.send_task("tasks.generate_image", args=[str(job_id)])
    return _response(job)
