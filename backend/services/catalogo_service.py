import uuid
from decimal import Decimal

from core.minio_client import MinIOClient
from models.catalogo import Catalogo, CatalogoItem
from repositories.catalogo_repo import CatalogoItemRepo, CatalogoRepo
from repositories.vton_job_repo import VTONJobRepo


class CatalogoNotFoundError(Exception):
    """Catalog does not exist or not owned by requesting mayorista."""


class CatalogoItemNotFoundError(Exception):
    """Catalog item does not exist in the specified catalog."""


class CatalogoOwnershipError(Exception):
    """Mayorista does not own the referenced catalog."""


class VTONJobNotFoundError(Exception):
    """VTON job does not exist."""


class VTONJobNotCompletedError(Exception):
    """VTON job must be completed before adding to catalog."""


class VTONJobOwnershipError(Exception):
    """VTON job does not belong to the requesting mayorista."""


class ReorderValidationError(Exception):
    """Reorder request does not contain exact bijection of catalog items."""


class EmptyCatalogCannotPublishError(Exception):
    """Raised when attempting to publish a catalog with 0 items."""


class InvalidCatalogStatusError(Exception):
    """Raised when status value is not 'draft' or 'published'."""


class CatalogoService:
    """Handles catalog creation and item lifecycle management."""

    def __init__(
        self,
        catalogo_repo: CatalogoRepo,
        catalogo_item_repo: CatalogoItemRepo,
        vton_job_repo: VTONJobRepo,
        minio_client: MinIOClient,
    ) -> None:
        self._catalogo_repo = catalogo_repo
        self._item_repo = catalogo_item_repo
        self._vton_job_repo = vton_job_repo
        self._minio = minio_client

    async def create_catalog(
        self, mayorista_id: uuid.UUID, name: str
    ) -> Catalogo:
        """Create a new catalog in draft status."""
        catalogo = Catalogo(
            mayorista_id=mayorista_id,
            name=name,
            status="draft",
            item_count=0,
        )
        return await self._catalogo_repo.create(catalogo)

    async def add_item(
        self,
        catalog_id: uuid.UUID,
        vton_job_id: uuid.UUID,
        garment_name: str,
        price: Decimal,
        cloth_type: str,
        sku: str,
        mayorista_id: uuid.UUID,
    ) -> tuple[CatalogoItem, str]:
        """Add a completed VTON result as a catalog item.

        Validates catalog ownership, VTON job completion, and job ownership.
        Returns the created item and a pre-signed URL for the image.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If catalog doesn't belong to mayorista.
            VTONJobNotFoundError: If VTON job doesn't exist.
            VTONJobNotCompletedError: If VTON job isn't completed.
            VTONJobOwnershipError: If VTON job doesn't belong to mayorista.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        vton_job = await self._vton_job_repo.get_by_id(vton_job_id)
        if vton_job is None:
            raise VTONJobNotFoundError("VTON job not found")

        if vton_job.status != "completed":
            raise VTONJobNotCompletedError(
                "Job must be completed before adding to catalog"
            )

        if vton_job.mayorista_id != mayorista_id:
            raise VTONJobOwnershipError("You do not own this VTON job")

        max_position = await self._item_repo.get_max_position(catalog_id)
        next_position = max_position + 1

        item = CatalogoItem(
            catalog_id=catalog_id,
            vton_job_id=vton_job_id,
            garment_name=garment_name,
            price=price,
            cloth_type=cloth_type,
            sku=sku,
            image_key=vton_job.result_minio_key,
            position=next_position,
        )
        item = await self._item_repo.create(item)
        await self._catalogo_repo.increment_item_count(catalog_id)

        image_url = await self._minio.get_presigned_url(
            bucket="generated", key=item.image_key
        )

        return item, image_url

    async def remove_item(
        self,
        catalog_id: uuid.UUID,
        item_id: uuid.UUID,
        mayorista_id: uuid.UUID,
    ) -> None:
        """Remove an item from a catalog.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If catalog doesn't belong to mayorista.
            CatalogoItemNotFoundError: If item doesn't exist in catalog.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        deleted = await self._item_repo.delete(item_id, catalog_id)
        if not deleted:
            raise CatalogoItemNotFoundError("Item not found in this catalog")

        await self._catalogo_repo.decrement_item_count(catalog_id)

    async def reorder_items(
        self,
        catalog_id: uuid.UUID,
        ordered_item_ids: list[uuid.UUID],
        mayorista_id: uuid.UUID,
    ) -> list[tuple[CatalogoItem, str]]:
        """Reorder items within a catalog atomically.

        Validates bijection: ordered_item_ids must contain exactly the same
        set of IDs as current catalog items. Positions are re-normalized
        to consecutive integers starting from 1.

        Returns list of (item, image_url) tuples in new order.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If catalog doesn't belong to mayorista.
            ReorderValidationError: If ordered_item_ids is not a bijection.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        current_items = await self._item_repo.get_all_by_catalog(catalog_id)
        current_ids = {item.id for item in current_items}
        requested_ids = set(ordered_item_ids)

        if len(ordered_item_ids) != len(requested_ids):
            raise ReorderValidationError(
                "Duplicate IDs in reorder request"
            )

        if current_ids != requested_ids:
            raise ReorderValidationError(
                "All catalog items must be included in the reorder request"
            )

        item_positions = {
            item_id: position + 1
            for position, item_id in enumerate(ordered_item_ids)
        }
        await self._item_repo.update_positions(item_positions)

        reordered_items = await self._item_repo.get_all_by_catalog(catalog_id)
        result = []
        for item in reordered_items:
            image_url = await self._minio.get_presigned_url(
                bucket="generated", key=item.image_key
            )
            result.append((item, image_url))

        return result

    async def rename_catalog(
        self, catalog_id: uuid.UUID, mayorista_id: uuid.UUID, new_name: str
    ) -> Catalogo:
        """Rename a catalog.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If mayorista doesn't own the catalog.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        updated = await self._catalogo_repo.update_name(catalog_id, new_name)
        return updated

    async def update_catalog_status(
        self, catalog_id: uuid.UUID, mayorista_id: uuid.UUID, new_status: str
    ) -> Catalogo:
        """Update catalog status (publish/unpublish).

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If mayorista doesn't own the catalog.
            InvalidCatalogStatusError: If status is not 'draft' or 'published'.
            EmptyCatalogCannotPublishError: If publishing empty catalog.
        """
        if new_status not in ("draft", "published"):
            raise InvalidCatalogStatusError(
                "Status must be 'draft' or 'published'"
            )

        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        if new_status == "published" and catalogo.item_count == 0:
            raise EmptyCatalogCannotPublishError(
                "Cannot publish an empty catalog"
            )

        if catalogo.status == new_status:
            return catalogo

        updated = await self._catalogo_repo.update_status(
            catalog_id, new_status
        )
        return updated

    async def delete_catalog(
        self, catalog_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> None:
        """Delete a catalog and all its items.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If mayorista doesn't own the catalog.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        await self._item_repo.delete_all_by_catalog(catalog_id)
        await self._catalogo_repo.delete(catalog_id)

    async def list_catalogs(
        self, mayorista_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Catalogo], int]:
        """List catalogs owned by mayorista with pagination."""
        return await self._catalogo_repo.list_by_mayorista(
            mayorista_id, page, page_size
        )

    async def get_catalog_with_items(
        self, catalog_id: uuid.UUID, mayorista_id: uuid.UUID
    ) -> tuple[Catalogo, list[tuple[CatalogoItem, str]]]:
        """Get a catalog with its items and pre-signed image URLs.

        Raises:
            CatalogoNotFoundError: If catalog doesn't exist.
            CatalogoOwnershipError: If mayorista doesn't own the catalog.
        """
        catalogo = await self._catalogo_repo.get_by_id_and_mayorista(
            catalog_id, mayorista_id
        )
        if catalogo is None:
            exists = await self._catalogo_repo.get_by_id(catalog_id)
            if exists is None:
                raise CatalogoNotFoundError("Catalog not found")
            raise CatalogoOwnershipError("You do not own this catalog")

        items = await self._item_repo.get_all_by_catalog(catalog_id)
        items_with_urls = []
        for item in items:
            image_url = await self._minio.get_presigned_url(
                bucket="generated", key=item.image_key
            )
            items_with_urls.append((item, image_url))

        return catalogo, items_with_urls
