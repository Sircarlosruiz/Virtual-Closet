"""Authenticated server-to-server bridge endpoints.

These routes are consumed by external applications (e.g. BFashion). They are
never cookie-authenticated; callers present ``X-Service-Id`` and
``X-Service-Secret`` headers and Virtual Closet validates an explicit product
link before doing any work.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.integration import (
    ProductGenerationBridgeRequest,
    ProductGenerationBridgeResponse,
    ProductGenerationBridgeStatusResponse,
)
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_service_client
from models.service_client import ServiceClient
from repositories.generation_job_repo import GenerationJobRepository
from repositories.mayorista_repo import MayoristaRepository
from repositories.product_link_repo import ProductLinkRepository
from services.idempotency_service import IdempotencyConflictError
from services.image_generation_service import ImageGenerationService
from services.integration_service import (
    BridgeGenerationJobNotFoundError,
    IntegrationService,
    StaffNotAuthorizedError,
)
from services.product_link_service import (
    ProductLinkMismatchError,
    ProductLinkNotFoundError,
    ProductLinkService,
)

router = APIRouter(prefix="/api/integration/v1", tags=["integration"])


def _get_service(db: AsyncSession = Depends(get_db)) -> IntegrationService:
    jobs = GenerationJobRepository(db)
    return IntegrationService(
        product_links=ProductLinkService(ProductLinkRepository(db)),
        mayoristas=MayoristaRepository(db),
        image_generation=ImageGenerationService(jobs),
        jobs=jobs,
    )


@router.post(
    "/products/generation-jobs",
    response_model=ProductGenerationBridgeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_product_generation_job(
    body: ProductGenerationBridgeRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    service_client: ServiceClient = Depends(get_service_client),
    service: IntegrationService = Depends(_get_service),
) -> ProductGenerationBridgeResponse:
    try:
        job, created, link = await service.create_product_generation(
            service_client=service_client,
            staff_id=body.staff_id,
            external_product_id=body.external_product_id,
            external_wholesaler_id=body.external_wholesaler_id,
            generation=body.generation,
            idempotency_key=idempotency_key,
        )
    except ProductLinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ProductLinkMismatchError, StaffNotAuthorizedError) as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if created:
        celery_app.send_task("tasks.generate_image", args=[str(job.id)])

    return ProductGenerationBridgeResponse(
        job_id=job.id,
        external_product_id=link.external_product_id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
    )


@router.get(
    "/products/{external_product_id}/generation-jobs/{job_id}",
    response_model=ProductGenerationBridgeStatusResponse,
)
async def get_product_generation_job(
    external_product_id: str,
    job_id: UUID,
    external_wholesaler_id: str | None = Query(None, alias="wholesaler_id"),
    service_client: ServiceClient = Depends(get_service_client),
    service: IntegrationService = Depends(_get_service),
) -> ProductGenerationBridgeStatusResponse:
    try:
        job, link = await service.get_product_generation(
            service_client=service_client,
            external_product_id=external_product_id,
            external_wholesaler_id=external_wholesaler_id,
            job_id=job_id,
        )
    except ProductLinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProductLinkMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except BridgeGenerationJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ProductGenerationBridgeStatusResponse(
        job_id=job.id,
        external_product_id=link.external_product_id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
