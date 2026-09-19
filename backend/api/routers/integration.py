"""Authenticated server-to-server bridge endpoints.

These routes are consumed by external applications (e.g. BFashion). They are
never cookie-authenticated; callers present ``X-Service-Id`` and
``X-Service-Secret`` headers and Virtual Closet validates an explicit product
link before doing any work.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.integration import (
    PhotoshootCatalogModel,
    PhotoshootCatalogTemplate,
    PhotoshootClothTypeOption,
    PhotoshootCreateRequest,
    PhotoshootCreateResponse,
    PhotoshootOptionsResponse,
    PhotoshootStageResponse,
    ProductGenerationBridgeRequest,
    ProductGenerationBridgeResponse,
    ProductGenerationBridgeStatusResponse,
    ProductLinkCreateRequest,
    ProductLinkCreateResponse,
    ProductPublicationBridgeRequest,
    SourceImageConfirmRequest,
    SourceImageConfirmResponse,
    SourceImagePresignRequest,
    SourceImagePresignResponse,
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
from core.minio_client import MinIOClient
from models.service_client import ServiceClient
from repositories.generation_job_repo import GenerationJobRepository
from repositories.image_template_repo import ImageTemplateRepository
from repositories.mayorista_repo import MayoristaRepository
from repositories.media_repo import ModelPhotoRepo
from repositories.model_repo import ModelRepo
from repositories.prenda_repo import PrendaRepository
from repositories.product_link_repo import ProductLinkRepository
from repositories.staff_identity_link_repo import StaffIdentityLinkRepository
from services.idempotency_service import IdempotencyConflictError
from services.photoshoot_catalog_service import (
    PhotoshootCatalogError,
    PhotoshootCatalogNotVisibleError,
    PhotoshootCatalogService,
    PhotoshootOptionsCatalog,
)
from services.photoshoot_errors import PhotoshootError
from services.photoshoot_submission_service import (
    PhotoshootSubmissionService,
    build_submission_service,
)
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
from services.source_image_intake_service import (
    SourceImageConfirmResult,
    SourceImageForbiddenError,
    SourceImageIntakeError,
    SourceImageNotUploadedError,
    SourceImagePresignResult,
    SourceImageProductNotFoundError,
    SourceImageRejectedError,
    SourceImageValidationError,
    StorageUnavailableError,
    build_intake_service,
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


def _source_image_intake_service(db: AsyncSession = Depends(get_db)):
    return build_intake_service(db)


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


def _photoshoot_submission_service(
    db: AsyncSession = Depends(get_db),
) -> PhotoshootSubmissionService:
    return build_submission_service(db)


def _photoshoot_catalog_service(
    db: AsyncSession = Depends(get_db),
) -> PhotoshootCatalogService:
    return PhotoshootCatalogService(
        product_links=ProductLinkService(ProductLinkRepository(db)),
        templates=ImageTemplateRepository(db),
        models=ModelRepo(db),
        photos=ModelPhotoRepo(db),
        minio=MinIOClient(),
    )


def _if_none_match_tokens(header: str | None) -> set[str]:
    if not header:
        return set()
    tokens: set[str] = set()
    for raw in header.split(","):
        token = raw.strip()
        if not token or token == "*":
            continue
        if token.startswith("W/"):
            token = token[2:].strip()
        tokens.add(token.strip('"'))
    return tokens


def _weak_etag(catalog_version: str) -> str:
    return f'W/"{catalog_version}"'


def _catalog_cache_headers(catalog_version: str) -> dict[str, str]:
    return {
        "ETag": _weak_etag(catalog_version),
        "Cache-Control": "private, no-cache",
    }


def _catalog_response(catalog: PhotoshootOptionsCatalog) -> PhotoshootOptionsResponse:
    return PhotoshootOptionsResponse(
        templates=[
            PhotoshootCatalogTemplate(
                id=row.id,
                name=row.name,
                scope=row.scope,  # type: ignore[arg-type]
                wholesaler_scope=row.wholesaler_scope,
                version=row.version,
                model=row.model,
                background=row.background,
                colors=row.colors,
                rack=row.rack,
                updated_at=row.updated_at,
            )
            for row in catalog.templates
        ],
        models=[
            PhotoshootCatalogModel(
                id=row.id,
                name=row.name,
                available_poses=list(row.available_poses),  # type: ignore[arg-type]
                preview_url=row.preview_url,
            )
            for row in catalog.models
        ],
        cloth_types=[
            PhotoshootClothTypeOption(value=item.value, label=item.label)
            for item in catalog.cloth_types
        ],
        background_suggestions=list(catalog.background_suggestions),
        color_suggestions=list(catalog.color_suggestions),
        max_pose_count=catalog.max_pose_count,
        catalog_version=catalog.catalog_version,
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


@router.get(
    "/products/{external_product_id}/photoshoot-options",
    response_model=PhotoshootOptionsResponse,
)
async def get_photoshoot_options(
    external_product_id: str = Path(min_length=1, max_length=255),
    external_wholesaler_id: str | None = Query(None, max_length=255),
    if_none_match: str | None = Header(None, alias="If-None-Match"),
    service_client: ServiceClient = Depends(get_service_client),
    service: PhotoshootCatalogService = Depends(_photoshoot_catalog_service),
) -> Response:
    try:
        catalog = await service.get_photoshoot_options(
            client=service_client,
            external_product_id=external_product_id,
            external_wholesaler_id=external_wholesaler_id,
        )
    except (PhotoshootCatalogNotVisibleError, PhotoshootCatalogError) as exc:
        raise _domain_http_error(exc) from exc

    headers = _catalog_cache_headers(catalog.catalog_version)
    if catalog.catalog_version in _if_none_match_tokens(if_none_match):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    signed = await service.with_preview_urls(catalog)
    payload = _catalog_response(signed)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


@router.post(
    "/products/{external_product_id}/photoshoots",
    response_model=PhotoshootCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_photoshoot(
    external_product_id: str,
    body: PhotoshootCreateRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    service_client: ServiceClient = Depends(get_service_client),
    service: PhotoshootSubmissionService = Depends(_photoshoot_submission_service),
) -> PhotoshootCreateResponse:
    try:
        result = await service.submit(
            client=service_client,
            external_product_id=external_product_id,
            staff_id=body.staff_id,
            source_image_id=body.source_image_id,
            input_kind=body.input_kind,
            model_ids=body.model_ids,
            cloth_type=body.cloth_type,
            pose_ids=list(body.pose_ids) if body.pose_ids is not None else None,
            pose_count=body.pose_count,
            template_id=body.template_id,
            background=body.background,
            colors=body.colors,
            overlay=body.overlay.model_dump() if body.overlay else None,
            variant_key=body.variant_key,
            external_wholesaler_id=body.external_wholesaler_id,
            idempotency_key=idempotency_key,
        )
    except (StaffIdentityError, PhotoshootError) as exc:
        raise _domain_http_error(exc) from exc

    return PhotoshootCreateResponse(
        photoshoot_id=result.photoshoot.id,
        external_product_id=result.external_product_id,
        status=result.photoshoot.status,
        expected_results=result.photoshoot.expected_results,
        stages=[
            PhotoshootStageResponse(name=stage.name, status=stage.status)
            for stage in result.stages
        ],
        created_at=result.photoshoot.created_at,
    )


@router.post(
    "/products/{external_product_id}/source-images:presign",
    response_model=SourceImagePresignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def presign_source_image(
    external_product_id: str,
    body: SourceImagePresignRequest,
    service_client: ServiceClient = Depends(get_service_client),
    service=Depends(_source_image_intake_service),
) -> SourceImagePresignResponse:
    try:
        result: SourceImagePresignResult = await service.presign(
            client=service_client,
            external_product_id=external_product_id,
            staff_id=body.staff_id,
            kind=body.kind,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
            filename=body.filename,
            external_wholesaler_id=body.external_wholesaler_id,
        )
    except (
        StaffForbiddenError,
        SourceImageProductNotFoundError,
        SourceImageValidationError,
        StorageUnavailableError,
        SourceImageIntakeError,
        StaffIdentityError,
    ) as exc:
        raise _domain_http_error(exc) from exc

    return SourceImagePresignResponse(
        source_image_id=result.reservation.id,
        upload_url=result.upload_url,
        method="PUT",
        headers={"Content-Type": result.reservation.declared_content_type},
        expires_in=result.expires_in,
        storage_key=result.reservation.storage_key,
    )


@router.post(
    "/products/{external_product_id}/source-images/{source_image_id}:confirm",
    response_model=SourceImageConfirmResponse,
)
async def confirm_source_image(
    external_product_id: str,
    source_image_id: UUID,
    body: SourceImageConfirmRequest,
    service_client: ServiceClient = Depends(get_service_client),
    service=Depends(_source_image_intake_service),
) -> SourceImageConfirmResponse:
    try:
        result: SourceImageConfirmResult = await service.confirm(
            client=service_client,
            external_product_id=external_product_id,
            source_image_id=source_image_id,
            staff_id=body.staff_id,
            checksum_sha256=body.checksum_sha256,
            external_wholesaler_id=body.external_wholesaler_id,
        )
    except (
        StaffForbiddenError,
        SourceImageProductNotFoundError,
        SourceImageForbiddenError,
        SourceImageNotUploadedError,
        SourceImageRejectedError,
        StorageUnavailableError,
        SourceImageIntakeError,
        StaffIdentityError,
    ) as exc:
        raise _domain_http_error(exc) from exc

    reservation = result.reservation
    return SourceImageConfirmResponse(
        source_image_id=reservation.id,
        kind=reservation.kind,  # type: ignore[arg-type]
        status="ready",
        content_type=reservation.actual_content_type
        or reservation.declared_content_type,
        size_bytes=reservation.actual_size_bytes
        or reservation.declared_size_bytes,
        preview_url=result.preview_url,
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
