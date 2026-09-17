from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.template import (
    ImageTemplateCreateRequest,
    ImageTemplateResponse,
    ImageTemplateUpdateRequest,
    TemplateScope,
    TemplateStatus,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.image_template_repo import ImageTemplateRepository
from services.template_lifecycle_service import (
    TemplateArchivedError,
    TemplateLifecycleService,
    TemplateNotFoundError,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])

_STAFF_ROLES = {"admin", "owner", "staff"}


def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateLifecycleService:
    return TemplateLifecycleService(ImageTemplateRepository(db))


def _require_staff(mayorista: Mayorista) -> None:
    if mayorista.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )


@router.post(
    "", response_model=ImageTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_template(
    body: ImageTemplateCreateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> ImageTemplateResponse:
    _require_staff(mayorista)
    template = await service.create_template(mayorista.id, body)
    return ImageTemplateResponse.model_validate(template)


@router.get("", response_model=list[ImageTemplateResponse])
async def list_templates(
    scope: TemplateScope | None = None,
    wholesaler_id: UUID | None = None,
    status_filter: TemplateStatus | None = None,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> list[ImageTemplateResponse]:
    _require_staff(mayorista)
    templates = await service.list_administrative(
        scope=scope.value if scope else None,
        wholesaler_id=wholesaler_id,
        status=status_filter.value if status_filter else None,
    )
    return [ImageTemplateResponse.model_validate(t) for t in templates]


@router.get("/selectable", response_model=list[ImageTemplateResponse])
async def list_selectable_templates(
    wholesaler_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> list[ImageTemplateResponse]:
    _require_staff(mayorista)
    templates = await service.list_selectable(wholesaler_id)
    return [ImageTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=ImageTemplateResponse)
async def get_template(
    template_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> ImageTemplateResponse:
    _require_staff(mayorista)
    try:
        template = await service.get_by_id(template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return ImageTemplateResponse.model_validate(template)


@router.patch("/{template_id}", response_model=ImageTemplateResponse)
async def revise_template(
    template_id: UUID,
    body: ImageTemplateUpdateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> ImageTemplateResponse:
    _require_staff(mayorista)
    try:
        template = await service.revise_template(template_id, body)
    except TemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TemplateArchivedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return ImageTemplateResponse.model_validate(template)


@router.post("/{template_id}/archive", response_model=ImageTemplateResponse)
async def archive_template(
    template_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    service: TemplateLifecycleService = Depends(_get_service),
) -> ImageTemplateResponse:
    _require_staff(mayorista)
    try:
        template = await service.archive_template(template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return ImageTemplateResponse.model_validate(template)
