"""Resolve explicit cross-application product links, fail-closed."""

from uuid import UUID

from models.product_link import ProductLink
from repositories.product_link_repo import ProductLinkRepository


class ProductLinkError(Exception):
    """Base error for product link resolution."""


class ProductLinkNotFoundError(ProductLinkError):
    """No active link exists for the requested external product."""


class ProductLinkMismatchError(ProductLinkError):
    """The link exists but does not belong to the caller's tenant/wholesaler."""


class ProductLinkService:
    """Validates that an external product maps to a Virtual Closet owner.

    Ownership is read exclusively from the persisted ``ProductLink``. External
    identifiers are never trusted as proof of ownership.
    """

    def __init__(self, repository: ProductLinkRepository) -> None:
        self._repository = repository

    async def resolve_active_link(
        self,
        system: str,
        external_product_id: str,
        external_wholesaler_id: str | None,
        tenant_id: UUID,
    ) -> ProductLink:
        link = await self._repository.get_by_external_product(system, external_product_id)
        if link is None or not link.is_active:
            raise ProductLinkNotFoundError("Product link not found")

        if link.tenant_id != tenant_id:
            raise ProductLinkMismatchError("Product link belongs to a different tenant")

        if link.external_wholesaler_id is not None and (
            external_wholesaler_id is None
            or external_wholesaler_id != link.external_wholesaler_id
        ):
            raise ProductLinkMismatchError("Product link wholesaler does not match")

        return link

    async def resolve_owned_link(
        self, product_link_id: UUID, tenant_id: UUID
    ) -> ProductLink:
        """Resolve a link by id for cookie-authenticated staff.

        Ownership still comes from the persisted row; the caller tenant must
        match. Unknown, inactive, or cross-tenant links fail closed.
        """
        link = await self._repository.get_by_id(product_link_id)
        if link is None or not link.is_active:
            raise ProductLinkNotFoundError("Product link not found")
        if link.tenant_id != tenant_id:
            raise ProductLinkMismatchError("Product link belongs to a different tenant")
        return link
