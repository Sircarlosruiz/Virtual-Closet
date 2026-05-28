import uuid

from core.minio_client import MinIOClient
from models.catalogo import Catalogo, CatalogoItem
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo


class CatalogoNotFoundError(Exception):
    """Catalog not found or not published."""


class CatalogoOwnershipError(Exception):
    """Catalog belongs to a different mayorista."""


class PortalCatalogService:
    """Read-only catalog access for buyer portal."""

    def __init__(
        self,
        catalogo_repo: CatalogoRepo,
        catalogo_item_repo: CatalogoItemRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._catalogo_repo = catalogo_repo
        self._item_repo = catalogo_item_repo
        self._minio = minio_client

    async def list_published_catalogs(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Catalogo], int]:
        """List published catalogs for buyer's mayorista."""
        return await self._catalogo_repo.list_published_by_mayorista(
            mayorista_id, page, page_size
        )

    async def get_published_catalog(
        self, catalog_id: uuid.UUID, buyer_mayorista_id: uuid.UUID
    ) -> tuple[Catalogo, list[tuple[CatalogoItem, str]]]:
        """Get published catalog with items and pre-signed URLs.

        Returns:
            tuple[Catalogo, list[tuple[CatalogoItem, str]]]: Catalog and list of (item, image_url) tuples.

        Raises:
            CatalogoNotFoundError: If catalog not found or not published.
            CatalogoOwnershipError: If catalog belongs to different mayorista.
        """
        catalogo = await self._catalogo_repo.get_by_id(catalog_id)

        if not catalogo or catalogo.status != "published":
            raise CatalogoNotFoundError("Catalog not found")

        if catalogo.mayorista_id != buyer_mayorista_id:
            raise CatalogoOwnershipError("Access denied")

        items = await self._item_repo.get_all_by_catalog(catalog_id)
        items_with_urls = []
        for item in items:
            image_url = await self._minio.get_presigned_url(
                bucket="generated", key=item.image_key
            )
            items_with_urls.append((item, image_url))

        return catalogo, items_with_urls
