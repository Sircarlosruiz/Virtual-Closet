"""Staff cookie-authenticated publication selection and retry."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.publication import (
    PublicationCandidateResponse,
    PublicationDecisionRequest,
    PublicationResponse,
    SyncDeliveryResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from models.publication import PublicationSelection, SyncDelivery
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.composition_version_repo import CompositionVersionRepository
from repositories.generation_job_repo import GenerationJobRepository
from repositories.product_image_repo import ProductImageRepository
from repositories.product_link_repo import ProductLinkRepository
from repositories.product_overlay_repo import ProductOverlayRepository
from repositories.publication_selection_repo import PublicationSelectionRepository
from repositories.sync_delivery_repo import SyncDeliveryRepository
from services.bfashion_sync_adapter import (
    BFashionSyncAdapter,
    HttpBFashionSyncAdapter,
)
from services.product_link_service import (
    ProductLinkMismatchError,
    ProductLinkNotFoundError,
    ProductLinkService,
)
from services.publication_service import (
    CandidateNotEligibleError,
    DiscardedCannotDeliverError,
    PublicationNotFoundError,
    PublicationService,
)
from services.sync_delivery_service import SyncDeliveryService

router = APIRouter(prefix="/api/publications", tags=["publications"])
candidates_router = APIRouter(prefix="/api/generation-jobs", tags=["publications"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def get_bfashion_adapter() -> BFashionSyncAdapter:
    return HttpBFashionSyncAdapter()


def get_publication_service(db: AsyncSession = Depends(get_db)) -> PublicationService:
    return PublicationService(
        db,
        PublicationSelectionRepository(db),
        GenerationJobRepository(db),
        ProductOverlayRepository(db),
        CompositionVersionRepository(db),
        ProductLinkService(ProductLinkRepository(db)),
    )


def get_sync_service(
    db: AsyncSession = Depends(get_db),
    bfashion: BFashionSyncAdapter = Depends(get_bfashion_adapter),
) -> SyncDeliveryService:
    return SyncDeliveryService(
        db,
        SyncDeliveryRepository(db),
        ProductImageRepository(db),
        CompositionSnapshotRepository(db),
        bfashion,
    )


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )
    if mayorista.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff actor does not belong to this tenant",
        )


def _publication_response(
    selection: PublicationSelection, deliveries: list[SyncDelivery]
) -> PublicationResponse:
    return PublicationResponse(
        id=selection.id,
        product_link_id=selection.product_link_id,
        generation_job_id=selection.generation_job_id,
        composition_version_id=selection.composition_version_id,
        decision=selection.decision,
        deliveries=[SyncDeliveryResponse.model_validate(item) for item in deliveries],
        created_at=selection.created_at,
        updated_at=selection.updated_at,
    )


def _map_publication_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProductLinkNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProductLinkMismatchError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, PublicationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CandidateNotEligibleError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DiscardedCannotDeliverError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise exc


@router.post(
    "", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED
)
async def create_publication(
    body: PublicationDecisionRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    _require_staff(mayorista)
    try:
        link = await publication.resolve_owned_link(
            body.product_link_id, mayorista.tenant_id
        )
        if mayorista.tenant_id != link.tenant_id:
            raise ProductLinkMismatchError("Staff actor does not belong to this tenant")
        selection, job, version = await publication.record_decision(
            link,
            mayorista.id,
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
        PublicationNotFoundError,
        CandidateNotEligibleError,
        DiscardedCannotDeliverError,
    ) as exc:
        raise _map_publication_error(exc) from exc
    return _publication_response(selection, deliveries)


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_publication(
    publication_id: UUID,
    product_link_id: UUID = Query(...),
    mayorista: Mayorista = Depends(get_current_mayorista),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    _require_staff(mayorista)
    try:
        link = await publication.resolve_owned_link(
            product_link_id, mayorista.tenant_id
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


@router.post("/{publication_id}/retry", response_model=PublicationResponse)
async def retry_publication(
    publication_id: UUID,
    product_link_id: UUID = Query(...),
    mayorista: Mayorista = Depends(get_current_mayorista),
    publication: PublicationService = Depends(get_publication_service),
    sync: SyncDeliveryService = Depends(get_sync_service),
) -> PublicationResponse:
    _require_staff(mayorista)
    try:
        link = await publication.resolve_owned_link(
            product_link_id, mayorista.tenant_id
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


@candidates_router.get(
    "/{job_id}/publication-candidates",
    response_model=list[PublicationCandidateResponse],
)
async def list_publication_candidates(
    job_id: UUID,
    product_link_id: UUID = Query(...),
    mayorista: Mayorista = Depends(get_current_mayorista),
    publication: PublicationService = Depends(get_publication_service),
) -> list[PublicationCandidateResponse]:
    _require_staff(mayorista)
    try:
        link = await publication.resolve_owned_link(
            product_link_id, mayorista.tenant_id
        )
        items = await publication.list_candidates(link, job_id)
    except (
        ProductLinkNotFoundError,
        ProductLinkMismatchError,
        PublicationNotFoundError,
    ) as exc:
        raise _map_publication_error(exc) from exc
    return [PublicationCandidateResponse.model_validate(item) for item in items]
