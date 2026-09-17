from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.schemas.image_generation import ImageGenerationRequest, ImageGenerationResponse
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.generation_job_repo import GenerationJobRepository
from services.image_generation_service import ImageGenerationService

router = APIRouter(prefix="/api/image-generation", tags=["image-generation"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ImageGenerationService:
    return ImageGenerationService(GenerationJobRepository(db))


def _response(job) -> ImageGenerationResponse:
    return ImageGenerationResponse(
        job_id=job.id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
    )


@router.post("/jobs", response_model=ImageGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_image_generation_job(
    body: ImageGenerationRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ImageGenerationService = Depends(_get_service),
) -> ImageGenerationResponse:
    if mayorista.role not in {"admin", "owner", "staff"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")

    job = await service.create_job(mayorista.id, body)
    celery_app.send_task("tasks.generate_image", args=[str(job.id)])
    return _response(job)


@router.get("/jobs/{job_id}", response_model=ImageGenerationResponse)
async def get_image_generation_job(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: ImageGenerationService = Depends(_get_service),
) -> ImageGenerationResponse:
    job = await service.get_job(job_id, mayorista.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    return _response(job)
