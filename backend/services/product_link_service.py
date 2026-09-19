"""Resolve explicit cross-application product links, fail-closed."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.product_link import ProductLink
from models.service_client import ServiceClient
from repositories.prenda_repo import PrendaRepository
from repositories.product_link_repo import ProductLinkRepository
from services.staff_identity_service import StaffIdentityService

logger = logging.getLogger(__name__)


class ProductLinkError(Exception):
    """Base error for product link resolution."""

    code = "PRODUCT_LINK_ERROR"
    status_code = 400

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ProductLinkNotFoundError(ProductLinkError):
    """No active link exists for the requested external product."""


class ProductLinkMismatchError(ProductLinkError):
    """The link exists but does not belong to the caller's tenant/wholesaler."""

    code = "PRODUCT_LINK_WHOLESALER_MISMATCH"
    status_code = 403


class ProductLinkCrossTenantError(ProductLinkError):
    """The unique pair exists but belongs to another tenant."""

    code = "PRODUCT_LINK_TENANT_CONFLICT"
    status_code = 403


class ProductLinkInactiveError(ProductLinkError):
    """Create must not reactivate a deactivated link (ADR-059)."""

    code = "PRODUCT_LINK_INACTIVE"
    status_code = 409


class ProductLinkPrendaForbiddenError(ProductLinkError):
    """prenda_id does not belong to the resolved staff mirror."""

    code = "PRODUCT_LINK_PRENDA_FORBIDDEN"
    status_code = 403


class ProductLinkCreateResult:
    def __init__(self, link: ProductLink, created: bool) -> None:
        self.link = link
        self.created = created


class ProductLinkService:
    """Validates that an external product maps to a Virtual Closet owner.

    Ownership is read exclusively from the persisted ``ProductLink``. External
    identifiers are never trusted as proof of ownership.
    """

    def __init__(
        self,
        repository: ProductLinkRepository,
        db: AsyncSession | None = None,
        staff_identities: StaffIdentityService | None = None,
        prendas: PrendaRepository | None = None,
    ) -> None:
        self._repository = repository
        self._db = db
        self._staff_identities = staff_identities
        self._prendas = prendas

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

    async def create_link(
        self,
        client: ServiceClient,
        external_product_id: str,
        staff_id: UUID,
        external_wholesaler_id: str | None = None,
        prenda_id: UUID | None = None,
    ) -> ProductLinkCreateResult:
        """Idempotent create. Owner is the staff mirror (ADR-060)."""
        if self._db is None or self._staff_identities is None or self._prendas is None:
            raise RuntimeError("ProductLinkService is not configured for create_link")

        staff = await self._staff_identities.resolve_staff_identity(client, staff_id)

        if prenda_id is not None:
            prenda = await self._prendas.get_by_id(prenda_id, staff.id)
            if prenda is None:
                raise ProductLinkPrendaForbiddenError(
                    "Prenda does not belong to the authorized staff"
                )

        existing = await self._repository.get_by_external_product(
            client.system, external_product_id
        )
        if existing is not None:
            return self._replay_or_reject(client, existing, external_wholesaler_id)

        try:
            link = ProductLink(
                system=client.system,
                external_product_id=external_product_id,
                external_wholesaler_id=external_wholesaler_id,
                mayorista_id=staff.id,
                prenda_id=prenda_id,
                tenant_id=client.tenant_id,
                is_active=True,
                created_by=staff.id,
            )
            await self._repository.add(link)
            await self._db.commit()
            await self._db.refresh(link)
        except IntegrityError:
            await self._db.rollback()
            raced = await self._repository.get_by_external_product(
                client.system, external_product_id
            )
            if raced is None:
                raise
            return self._replay_or_reject(client, raced, external_wholesaler_id)

        logger.info(
            "product_link_created",
            extra={
                "product_link_id": str(link.id),
                "external_product_id": external_product_id,
                "system": client.system,
                "tenant_id": str(client.tenant_id),
                "link_created": True,
            },
        )
        return ProductLinkCreateResult(link, created=True)

    def _replay_or_reject(
        self,
        client: ServiceClient,
        existing: ProductLink,
        external_wholesaler_id: str | None,
    ) -> ProductLinkCreateResult:
        if existing.tenant_id != client.tenant_id:
            raise ProductLinkCrossTenantError(
                "Product link belongs to a different tenant"
            )
        if not existing.is_active:
            raise ProductLinkInactiveError(
                "Product link exists but is inactive"
            )
        if existing.external_wholesaler_id is not None and (
            external_wholesaler_id is None
            or external_wholesaler_id != existing.external_wholesaler_id
        ):
            raise ProductLinkMismatchError("Product link wholesaler does not match")

        logger.info(
            "product_link_replayed",
            extra={
                "product_link_id": str(existing.id),
                "external_product_id": existing.external_product_id,
                "system": client.system,
                "link_created": False,
            },
        )
        return ProductLinkCreateResult(existing, created=False)
