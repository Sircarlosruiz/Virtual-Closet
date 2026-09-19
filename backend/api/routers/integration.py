"""Authenticated server-to-server bridge endpoints.

These routes are consumed by external applications (e.g. BFashion). They are
never cookie-authenticated; callers present ``X-Service-Id`` and
``X-Service-Secret`` headers and Virtual Closet validates an explicit product
link before doing any work.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.integration import (
    ProductGenerationBridgeRequest,
    ProductGenerationBridgeResponse,
    ProductGenerationBridgeStatusResponse,
    ProductLinkCreateRequest,
    ProductLinkCreateResponse,
    ProductPublicationBridgeRequest,
    StaffIdentityProvisionRequest,
    StaffIdentityProvisionResponse,
    StaffIdentityRevokeResponse,
)
from api.schemas.publication import (
    PublicationCandidateResponse,
    PublicationResponse,
)
from api.routers.publication import (
    _map_publication_error,
    _publication_response,
    get_publication_service,
    get_sync_service,
)
from core.celery_app import app as celery_app
from core.database import get_db
from core.dependencies import get_service_client
from models.service_client import ServiceClient
from repositories.generation_job_repo import GenerationJobRepository
from repositories.mayorista_repo import MayoristaRepository
from repositories.prenda_repo import PrendaRepository
from repositories.product_link_repo import ProductLinkRepository
from repositories.staff_identity_link_repo import StaffIdentityLinkRepository
from services.idempotency_service import IdempotencyConflictError
from services.image_generation_service import ImageGenerationService
from services.integration_service import (
    BridgeGenerationJobNotFoundError,
    IntegrationService,
    StaffNotAuthorizedError,
)
from services.product_link_service import (
    ProductLinkCreateResult,
    ProductLinkCrossTenantError,
    ProductLinkError,
    ProductLinkInactiveError,
    ProductLinkMismatchError,
    ProductLinkNotFoundError,
    ProductLinkPrendaForbiddenError,
    ProductLinkService,
)
from services.staff_identity_service import (
    MirrorEmailConflictError,
    StaffForbiddenError,
    StaffIdentityError,
    StaffIdentityNotFoundError,
    StaffIdentityResult,
    StaffIdentityService,
)
from services.publication_service import (
    CandidateNotEligibleError,
    DiscardedCannotDeliverError,
    PublicationNotFoundError,
    PublicationService,
    preview_object_url,
)
from services.sync_delivery_service import SyncDeliveryService

router = APIRouter(prefix="/api/integration/v1", tags=["integration"])


def _get_service(db: AsyncSession = Depends(get_db)) -> IntegrationService:
    jobs = GenerationJobRepository(db)
    return IntegrationService(
        product_links=ProductLinkService(ProductLinkRepository(db)),
        mayoristas=MayoristaRepository(db),
        image_generation=ImageGenerationService(jobs),
        jobs=jobs,
    )


def _staff_identity_service(
    db: AsyncSession = Depends(get_db),
) -> StaffIdentityService:
    return StaffIdentityService(
        db,
        StaffIdentityLinkRepository(db),
        MayoristaRepository(db),
    )


def _product_link_write_service(
    db: AsyncSession = Depends(get_db),
) -> ProductLinkService:
    staff_identities = StaffIdentityService(
        db,
        StaffIdentityLinkRepository(db),
        MayoristaRepository(db),
    )
    return ProductLinkService(
        ProductLinkRepository(db),
        db=db,
        staff_identities=staff_identities,
        prendas=PrendaRepository(db),
    )


def _domain_http_error(exc: Exception) -> HTTPException:
    code = getattr(exc, "code", None)
    status_code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
    context = getattr(exc, "context", {})
    if code:
        return HTTPException(
            status_code=status_code,
            detail={"code": code, "message": str(exc), "context": context},
        )
    return HTTPException(status_code=status_code, detail=str(exc))


@router.post(
    "/product-links",
    response_model=ProductLinkCreateResponse,
)
async def create_product_link(
    body: ProductLinkCreateRequest,
    service_client: ServiceClient = Depends(get_service_client),
    service: ProductLinkService = Depends(_product_link_write_service),
) -> ProductLinkCreateResponse:
    try:
        result: ProductLinkCreateResult = await service.create_link(
            client=service_client,
            external_product_id=body.external_product_id,
            staff_id=body.staff_id,
            external_wholesaler_id=body.external_wholesaler_id,
            prenda_id=body.prenda_id,
        )
    except (
        StaffForbiddenError,
        ProductLinkCrossTenantError,
        ProductLinkInactiveError,
        ProductLinkPrendaForbiddenError,
        ProductLinkMismatchError,
        ProductLinkError,
        StaffIdentityError,
    ) as exc:
        raise _domain_http_error(exc) from exc

    payload = ProductLinkCreateResponse(
        product_link_id=result.link.id,
        external_product_id=result.link.external_product_id,
        mayorista_id=result.link.mayorista_id,
        tenant_id=result.link.tenant_id,
        is_active=result.link.is_active,
        created=result.created,
    )
    return JSONResponse(
        status_code=(
            status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        ),
        content=payload.model_dump(mode="json"),
    )


@router.post(
    "/staff-identities",
    response_model=StaffIdentityProvisionResponse,
)
async def provision_staff_identity(
    body: StaffIdentityProvisionRequest,
    service_client: ServiceClient = Depends(get_service_client),
    service: StaffIdentityService = Depends(_staff_identity_service),
) -> StaffIdentityProvisionResponse:
    try:
        result: StaffIdentityResult = await service.provision(
            client=service_client,
            external_staff_id=body.external_staff_id,
            email=str(body.email),
            display_name=body.display_name,
            role=body.role,
        )
    except (
        MirrorEmailConflictError,
        StaffForbiddenError,
        StaffIdentityError,
    ) as exc:
        raise _domain_http_error(exc) from exc

    status_code = (
        status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    )
    response = StaffIdentityProvisionResponse(
        staff_id=result.mayorista.id,
        external_staff_id=result.link.external_staff_id,
        email=result.mayorista.email,
        role=result.mayorista.role,
        is_active=result.link.is_active,
        created=result.created,
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


@router.post(
    "/staff-identities/{external_staff_id}:revoke",
    response_model=StaffIdentityRevokeResponse,
)
async def revoke_staff_identity(
    external_staff_id: str,
    service_client: ServiceClient = Depends(get_service_client),
    service: StaffIdentityService = Depends(_staff_identity_service),
) -> StaffIdentityRevokeResponse:
    try:
        result = await service.revoke(service_client, external_staff_id)
    except (StaffIdentityNotFoundError, StaffIdentityError) as exc:
        raise _domain_http_error(exc) from exc

    return StaffIdentityRevokeResponse(
        staff_id=result.mayorista.id,
        external_staff_id=result.link.external_staff_id,
        is_active=result.link.is_active,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (ProductLinkMismatchError, StaffNotAuthorizedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ProductLinkMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except BridgeGenerationJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return ProductGenerationBridgeStatusResponse(
        job_id=job.id,
        external_product_id=link.external_product_id,
        mode=job.mode,
        provider=job.provider,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        preview_url=await preview_object_url(job.result_key),
    )


@router.post(
    "/products/{external_product_id}/publications",
    response_model=PublicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_publication(
    external_product_id: str,
    body: ProductPublicationBridgeRequest,
    service_client: ServiceClient = Depends(get_service_client),
    integration: IntegrationService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    try:
        link = await integration.resolve_link(
            service_client,
            external_product_id,
            body.external_wholesaler_id,
        )
        await integration.authorize_staff(body.staff_id, link)
        selection, job, version = await publication.record_decision(
            link,
            body.staff_id,
            body.generation_job_id,
            body.composition_version_id,
            body.decision,
        )
        if selection.decision == "selected":
            deliveries = await sync.sync_selection(selection, link, job, version)
        else:
            await db.commit()
            deliveries = await sync.list_deliveries(selection.id)
    except (
        ProductLinkNotFoundError,
        ProductLinkMismatchError,
        StaffNotAuthorizedError,
        PublicationNotFoundError,
        CandidateNotEligibleError,
        DiscardedCannotDeliverError,
    ) as exc:
        if isinstance(exc, StaffNotAuthorizedError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        raise _map_publication_error(exc) from exc
    return _publication_response(selection, deliveries)


@router.get(
    "/products/{external_product_id}/publications/{publication_id}",
    response_model=PublicationResponse,
)
async def get_product_publication(
    external_product_id: str,
    publication_id: UUID,
    external_wholesaler_id: str | None = Query(None, alias="wholesaler_id"),
    service_client: ServiceClient = Depends(get_service_client),
    integration: IntegrationService = Depends(_get_service),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    try:
        link = await integration.resolve_link(
            service_client,
            external_product_id,
            external_wholesaler_id,
        )
        selection = await publication.get_owned_selection(publication_id, link)
        deliveries = await sync.list_deliveries(selection.id)
    except (
        ProductLinkNotFoundError,
        ProductLinkMismatchError,
        PublicationNotFoundError,
    ) as exc:
        raise _map_publication_error(exc) from exc
    return _publication_response(selection, deliveries)


@router.post(
    "/products/{external_product_id}/publications/{publication_id}/retry",
    response_model=PublicationResponse,
)
async def retry_product_publication(
    external_product_id: str,
    publication_id: UUID,
    external_wholesaler_id: str | None = Query(None, alias="wholesaler_id"),
    service_client: ServiceClient = Depends(get_service_client),
    integration: IntegrationService = Depends(_get_service),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    try:
        link = await integration.resolve_link(
            service_client,
            external_product_id,
            external_wholesaler_id,
        )
        selection = await publication.get_owned_selection(publication_id, link)
        job, version, _key = await publication.load_candidate(
            link, selection.generation_job_id, selection.composition_version_id
        )
        deliveries = await sync.sync_selection(
            selection, link, job, version, retry_only_failed=True
        )
    except (
        ProductLinkNotFoundError,
        ProductLinkMismatchError,
        PublicationNotFoundError,
        CandidateNotEligibleError,
        DiscardedCannotDeliverError,
    ) as exc:
        raise _map_publication_error(exc) from exc
    return _publication_response(selection, deliveries)


@router.get(
    "/products/{external_product_id}/generation-jobs/{job_id}/publication-candidates",
    response_model=list[PublicationCandidateResponse],
)
async def list_product_publication_candidates(
    external_product_id: str,
    job_id: UUID,
    external_wholesaler_id: str | None = Query(None, alias="wholesaler_id"),
    service_client: ServiceClient = Depends(get_service_client),
    integration: IntegrationService = Depends(_get_service),
    publication: PublicationService = Depends(get_publication_service),
) -> list[PublicationCandidateResponse]:
    try:
        link = await integration.resolve_link(
            service_client,
            external_product_id,
            external_wholesaler_id,
        )
        items = await publication.list_candidates(link, job_id)
    except (
        ProductLinkNotFoundError,
        ProductLinkMismatchError,
        PublicationNotFoundError,
    ) as exc:
        raise _map_publication_error(exc) from exc
    return [PublicationCandidateResponse.model_validate(item) for item in items]
