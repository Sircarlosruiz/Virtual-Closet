from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.catalogo import (
    CatalogoCreateRequest,
    CatalogoDetailResponse,
    CatalogoItemAddRequest,
    CatalogoItemResponse,
    CatalogoListResponse,
    CatalogoReorderItemResponse,
    CatalogoReorderRequest,
    CatalogoReorderResponse,
    CatalogoResponse,
    CatalogoUpdateRequest,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.minio_client import MinIOClient
from models.mayorista import Mayorista
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo
from repositories.vton_job_repo import VTONJobRepo
from services.catalogo_service import (
    CatalogoItemNotFoundError,
    CatalogoNotFoundError,
    CatalogoOwnershipError,
    CatalogoService,
    EmptyCatalogCannotPublishError,
    InvalidCatalogStatusError,
    ReorderValidationError,
    VTONJobNotCompletedError,
    VTONJobNotFoundError,
    VTONJobOwnershipError,
)

router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])


def _get_catalogo_service(db: AsyncSession = Depends(get_db)) -> CatalogoService:
    catalogo_repo = CatalogoRepo(db)
    catalogo_item_repo = CatalogoItemRepo(db)
    vton_job_repo = VTONJobRepo(db)
    minio_client = MinIOClient()
    return CatalogoService(
        catalogo_repo, catalogo_item_repo, vton_job_repo, minio_client
    )


@router.post(
    "",
    response_model=CatalogoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog(
    body: CatalogoCreateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Create a new catalog in draft status."""
    catalogo = await catalogo_service.create_catalog(
        mayorista_id=mayorista.id,
        name=body.name,
    )
    return catalogo


@router.get("", response_model=CatalogoListResponse)
async def list_catalogs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """List catalogs owned by the authenticated mayorista."""
    catalogs, total = await catalogo_service.list_catalogs(
        mayorista_id=mayorista.id,
        page=page,
        page_size=page_size,
    )
    return CatalogoListResponse(
        catalogs=catalogs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{catalog_id}", response_model=CatalogoDetailResponse)
async def get_catalog(
    catalog_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Get a catalog with its items and pre-signed image URLs."""
    try:
        catalogo, items_with_urls = await catalogo_service.get_catalog_with_items(
            catalog_id=catalog_id,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return CatalogoDetailResponse(
        id=catalogo.id,
        name=catalogo.name,
        status=catalogo.status,
        item_count=catalogo.item_count,
        created_at=catalogo.created_at,
        updated_at=catalogo.updated_at,
        items=[
            CatalogoItemResponse(
                id=item.id,
                catalog_id=item.catalog_id,
                vton_job_id=item.vton_job_id,
                image_url=image_url,
                garment_name=item.garment_name,
                price=item.price,
                cloth_type=item.cloth_type,
                sku=item.sku,
                position=item.position,
                created_at=item.created_at,
            )
            for item, image_url in items_with_urls
        ],
    )


@router.patch("/{catalog_id}", response_model=CatalogoResponse)
async def update_catalog(
    catalog_id: UUID,
    body: CatalogoUpdateRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Update catalog name and/or status."""
    try:
        catalogo = None

        if body.name is not None:
            catalogo = await catalogo_service.rename_catalog(
                catalog_id=catalog_id,
                mayorista_id=mayorista.id,
                new_name=body.name,
            )

        if body.status is not None:
            catalogo = await catalogo_service.update_catalog_status(
                catalog_id=catalog_id,
                mayorista_id=mayorista.id,
                new_status=body.status.value,
            )

        if catalogo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of 'name' or 'status' must be provided",
            )

        return catalogo

    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except InvalidCatalogStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except EmptyCatalogCannotPublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.delete("/{catalog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog(
    catalog_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Delete a catalog and all its items."""
    try:
        await catalogo_service.delete_catalog(
            catalog_id=catalog_id,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.post(
    "/{catalog_id}/items",
    response_model=CatalogoItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    catalog_id: UUID,
    body: CatalogoItemAddRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Add a completed VTON result as a catalog item."""
    try:
        item, image_url = await catalogo_service.add_item(
            catalog_id=catalog_id,
            vton_job_id=body.vton_job_id,
            garment_name=body.garment_name,
            price=body.price,
            cloth_type=body.cloth_type.value,
            sku=body.sku,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except VTONJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except VTONJobNotCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except VTONJobOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return CatalogoItemResponse(
        id=item.id,
        catalog_id=item.catalog_id,
        vton_job_id=item.vton_job_id,
        image_url=image_url,
        garment_name=item.garment_name,
        price=item.price,
        cloth_type=item.cloth_type,
        sku=item.sku,
        position=item.position,
        created_at=item.created_at,
    )


@router.delete(
    "/{catalog_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item(
    catalog_id: UUID,
    item_id: UUID,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Remove an item from a catalog."""
    try:
        await catalogo_service.remove_item(
            catalog_id=catalog_id,
            item_id=item_id,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except CatalogoItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch(
    "/{catalog_id}/items/reorder",
    response_model=CatalogoReorderResponse,
)
async def reorder_items(
    catalog_id: UUID,
    body: CatalogoReorderRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    catalogo_service: CatalogoService = Depends(_get_catalogo_service),
):
    """Reorder items within a catalog atomically."""
    try:
        items_with_urls = await catalogo_service.reorder_items(
            catalog_id=catalog_id,
            ordered_item_ids=body.ordered_item_ids,
            mayorista_id=mayorista.id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except ReorderValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return CatalogoReorderResponse(
        items=[
            CatalogoReorderItemResponse(
                id=item.id,
                position=item.position,
                garment_name=item.garment_name,
                image_url=image_url,
                price=item.price,
                cloth_type=item.cloth_type,
                sku=item.sku,
            )
            for item, image_url in items_with_urls
        ]
    )
