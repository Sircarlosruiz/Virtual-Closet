"""Tenant service for multi-tenancy management."""

import secrets
import uuid

from repositories.tenant_repo import TenantRepo
from models.tenant import Tenant


class TenantNotFoundError(Exception):
    """Tenant does not exist."""


class TenantInactiveError(Exception):
    """Tenant is not active."""


class TenantSlugConflictError(Exception):
    """Tenant slug already exists."""


class TenantService:
    """Handles tenant lifecycle management."""

    def __init__(self, tenant_repo: TenantRepo) -> None:
        self._tenant_repo = tenant_repo

    @staticmethod
    def _generate_slug(name: str) -> str:
        import re

        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug[:50]

    @staticmethod
    def _generate_buyer_link_secret() -> str:
        return secrets.token_hex(32)

    async def create_tenant(
        self,
        name: str,
        settings: dict | None = None,
    ) -> Tenant:
        """Create a new tenant.

        Args:
            name: Display name for the tenant.
            settings: Optional JSONB settings dict.

        Returns:
            The created Tenant.

        Raises:
            TenantSlugConflictError: If the generated slug already exists.
        """
        slug = self._generate_slug(name)

        exists = await self._tenant_repo.exists_by_slug(slug)
        if exists:
            raise TenantSlugConflictError(
                f"Tenant slug '{slug}' already exists"
            )

        tenant = Tenant(
            name=name,
            slug=slug,
            buyer_link_secret=self._generate_buyer_link_secret(),
            settings=settings or {},
        )
        return await self._tenant_repo.create(tenant)

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """Get a tenant by ID.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        if not tenant.is_active:
            raise TenantInactiveError("Tenant is not active")
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Get a tenant by slug.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
        """
        tenant = await self._tenant_repo.get_by_slug(slug)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        if not tenant.is_active:
            raise TenantInactiveError("Tenant is not active")
        return tenant

    async def update_tenant(
        self,
        tenant_id: uuid.UUID,
        name: str | None = None,
        settings: dict | None = None,
    ) -> Tenant:
        """Update tenant name and/or settings.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
            TenantSlugConflictError: If new name generates a conflicting slug.
        """
        tenant = await self.get_tenant(tenant_id)

        if name is not None:
            new_slug = self._generate_slug(name)
            if new_slug != tenant.slug:
                exists = await self._tenant_repo.exists_by_slug(new_slug)
                if exists:
                    raise TenantSlugConflictError(
                        f"Tenant slug '{new_slug}' already exists"
                    )
                tenant.slug = new_slug
            tenant.name = name

        if settings is not None:
            tenant.settings = settings

        return await self._tenant_repo.update(tenant)

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """Soft-delete a tenant.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        deactivated = await self._tenant_repo.deactivate(tenant_id)
        if deactivated is None:
            raise TenantNotFoundError("Tenant not found")
        return deactivated
