from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.customer import (
    MagicLinkRequest,
    PortalAuthResponse,
    PortalCatalogDetailResponse,
    PortalCatalogItemResponse,
    PortalCatalogListResponse,
    PortalCatalogResponse,
)
from core.config import settings
from core.database import get_db
from core.dependencies import get_current_buyer
from core.minio_client import MinIOClient
from models.customer import Customer
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo
from repositories.customer_repo import CustomerRepo
from services.customer_service import (
    CustomerService,
    InvalidTokenError,
)
from services.portal_catalog_service import (
    CatalogoNotFoundError,
    CatalogoOwnershipError,
    PortalCatalogService,
)
from services.token_service import TokenService

router = APIRouter(prefix="/api/portal", tags=["portal"])


def _get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    customer_repo = CustomerRepo(db)
    token_service = TokenService()
    return CustomerService(customer_repo, token_service)


def _get_portal_service(db: AsyncSession = Depends(get_db)) -> PortalCatalogService:
    catalogo_repo = CatalogoRepo(db)
    catalogo_item_repo = CatalogoItemRepo(db)
    minio_client = MinIOClient()
    return PortalCatalogService(catalogo_repo, catalogo_item_repo, minio_client)


@router.get("/auth", response_model=PortalAuthResponse)
async def authenticate_buyer(
    token: str,
    response: Response,
    customer_service: CustomerService = Depends(_get_customer_service),
):
    """Validate invitation or magic-link token and issue buyer session cookie."""
    try:
        customer = await customer_service.validate_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    token_service = TokenService()
    session_token = token_service.create_buyer_session(
        customer.id, customer.mayorista_id
    )

    response.set_cookie(
        key="buyer_session",
        value=session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path="/api/portal",
        max_age=7 * 24 * 60 * 60,
    )

    return PortalAuthResponse(
        message="Authentication successful",
        customer_id=customer.id,
        mayorista_id=customer.mayorista_id,
    )


@router.post("/magic-link")
async def request_magic_link(
    body: MagicLinkRequest,
    background_tasks: BackgroundTasks,
    customer_service: CustomerService = Depends(_get_customer_service),
):
    """Request a magic-link email for re-authentication. Always returns 200."""
    magic_link_token = await customer_service.request_magic_link(body.email)

    if magic_link_token:
        from services.email_service import send_magic_link_email

        customer = await customer_service._customer_repo.get_by_email(body.email)
        if customer:
            background_tasks.add_task(
                send_magic_link_email,
                customer_email=customer.email,
                customer_name=customer.name,
                magic_link_token=magic_link_token,
            )

    return {"message": "If an account exists, a magic link has been sent"}


@router.get("/catalogs", response_model=PortalCatalogListResponse)
async def list_catalogs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    buyer: Customer = Depends(get_current_buyer),
    portal_service: PortalCatalogService = Depends(_get_portal_service),
):
    """List published catalogs for authenticated buyer's mayorista."""
    catalogs, total = await portal_service.list_published_catalogs(
        mayorista_id=buyer.mayorista_id,
        page=page,
        page_size=page_size,
    )
    return PortalCatalogListResponse(
        catalogs=[PortalCatalogResponse.model_validate(c) for c in catalogs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/catalogs/{catalog_id}", response_model=PortalCatalogDetailResponse)
async def get_catalog(
    catalog_id: UUID,
    buyer: Customer = Depends(get_current_buyer),
    portal_service: PortalCatalogService = Depends(_get_portal_service),
):
    """Get published catalog detail with items."""
    try:
        catalogo, items_with_urls = await portal_service.get_published_catalog(
            catalog_id=catalog_id,
            buyer_mayorista_id=buyer.mayorista_id,
        )
    except CatalogoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CatalogoOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return PortalCatalogDetailResponse(
        id=catalogo.id,
        name=catalogo.name,
        status=catalogo.status,
        item_count=catalogo.item_count,
        created_at=catalogo.created_at,
        items=[
            PortalCatalogItemResponse(
                id=item.id,
                image_url=image_url,
                garment_name=item.garment_name,
                price=item.price,
                cloth_type=item.cloth_type,
                sku=item.sku,
                position=item.position,
            )
            for item, image_url in items_with_urls
        ],
    )
