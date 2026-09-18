from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.composition import (
    CompositionRequest,
    CompositionSummaryResponse,
    CompositionVersionResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.composition_snapshot_repo import CompositionSnapshotRepository
from repositories.composition_version_repo import CompositionVersionRepository
from repositories.generation_job_repo import GenerationJobRepository
from repositories.product_overlay_repo import ProductOverlayRepository
from services.composition_spec import InvalidSkuError, UnsupportedFontError
from services.sku_composition_service import (
    BaseImageUnavailableError,
    CompositionNotFoundError,
    GenerationJobNotFoundError,
    OverlayDoesNotFitError,
    SkuCompositionService,
)

router = APIRouter(prefix="/api/generation-jobs", tags=["composition"])
versions_router = APIRouter(prefix="/api/composition-versions", tags=["composition"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def _get_service(db: AsyncSession = Depends(get_db)) -> SkuCompositionService:
    return SkuCompositionService(
        ProductOverlayRepository(db),
        CompositionVersionRepository(db),
        GenerationJobRepository(db),
        CompositionSnapshotRepository(db),
    )


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )


@router.post("/{job_id}/composition", response_model=CompositionVersionResponse)
async def compose_sku_overlay(
    job_id: UUID,
    body: CompositionRequest,
    response: Response,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: SkuCompositionService = Depends(_get_service),
) -> CompositionVersionResponse:
    _require_staff(mayorista)
    try:
        result = await service.compose(mayorista.id, job_id, body)
    except GenerationJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CompositionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BaseImageUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (InvalidSkuError, UnsupportedFontError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except OverlayDoesNotFitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "OVERLAY_DOES_NOT_FIT",
                "message": str(exc),
                "context": {"version_id": str(exc.version_id)},
            },
        ) from exc

    response.status_code = (
        status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    )
    return CompositionVersionResponse.from_model(
        result.version, result.overlay.generation_job_id
    )


@router.get("/{job_id}/composition", response_model=CompositionSummaryResponse)
async def get_composition(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: SkuCompositionService = Depends(_get_service),
) -> CompositionSummaryResponse:
    _require_staff(mayorista)
    try:
        overlay, latest = await service.get_summary(mayorista.id, job_id)
    except GenerationJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CompositionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return CompositionSummaryResponse(
        overlay_id=overlay.id,
        generation_job_id=overlay.generation_job_id,
        base_image_key=overlay.base_image_key,
        latest_version=(
            CompositionVersionResponse.from_model(latest, overlay.generation_job_id)
            if latest
            else None
        ),
    )


@router.get(
    "/{job_id}/composition/versions",
    response_model=list[CompositionVersionResponse],
)
async def list_composition_versions(
    job_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: SkuCompositionService = Depends(_get_service),
) -> list[CompositionVersionResponse]:
    _require_staff(mayorista)
    try:
        overlay, versions = await service.list_versions(mayorista.id, job_id)
    except GenerationJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CompositionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return [
        CompositionVersionResponse.from_model(version, overlay.generation_job_id)
        for version in versions
    ]


@versions_router.get("/{version_id}", response_model=CompositionVersionResponse)
async def get_composition_version(
    version_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: SkuCompositionService = Depends(_get_service),
) -> CompositionVersionResponse:
    _require_staff(mayorista)
    try:
        overlay, version = await service.get_version(mayorista.id, version_id)
    except CompositionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return CompositionVersionResponse.from_model(version, overlay.generation_job_id)
