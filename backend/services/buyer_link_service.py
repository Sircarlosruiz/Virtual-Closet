"""Buyer link service for signed catalog access links."""

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from repositories.buyer_link_repo import BuyerLinkRepo
from repositories.tenant_repo import TenantRepo
from models.buyer_link import BuyerLink
from models.tenant import Tenant
from services.tenant_service import TenantNotFoundError, TenantInactiveError


class InvalidBuyerLinkError(Exception):
    """Buyer link token is invalid."""


class BuyerLinkExpiredError(Exception):
    """Buyer link token has expired."""


class InvalidCatalogScopeError(Exception):
    """Catalog scope is invalid or empty."""


DEFAULT_TTL_DAYS = 30
BUYER_LINK_ALGORITHM = "HS256"


class BuyerLinkService:
    """Handles buyer link generation and validation."""

    def __init__(
        self,
        buyer_link_repo: BuyerLinkRepo,
        tenant_repo: TenantRepo,
    ) -> None:
        self._buyer_link_repo = buyer_link_repo
        self._tenant_repo = tenant_repo

    async def generate_link(
        self,
        tenant_id: uuid.UUID,
        catalog_ids: list[uuid.UUID],
        created_by: uuid.UUID,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> tuple[BuyerLink, str]:
        """Generate a signed buyer link for catalog access.

        Args:
            tenant_id: The tenant owning the catalogs.
            catalog_ids: List of catalog UUIDs to grant access to.
            created_by: UUID of the user generating the link.
            ttl_days: Time-to-live in days (default: 30).

        Returns:
            Tuple of (BuyerLink record, signed JWT string).

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
            InvalidCatalogScopeError: If catalog_ids is empty.
        """
        if not catalog_ids:
            raise InvalidCatalogScopeError(
                "At least one catalog ID is required"
            )

        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        if not tenant.is_active:
            raise TenantInactiveError("Tenant is not active")

        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        jti = uuid.uuid4().hex

        payload = {
            "sub": str(tenant_id),
            "catalog_ids": [str(cid) for cid in catalog_ids],
            "jti": jti,
            "exp": expires_at,
            "type": "buyer_link",
        }

        signed_token = jwt.encode(
            payload,
            tenant.buyer_link_secret,
            algorithm=BUYER_LINK_ALGORITHM,
        )

        link = BuyerLink(
            tenant_id=tenant_id,
            catalog_ids=catalog_ids,
            token_jti=jti,
            expires_at=expires_at,
            created_by=created_by,
        )
        link = await self._buyer_link_repo.create(link)

        return link, signed_token

    def validate_link(self, token: str) -> dict:
        """Validate a buyer link token (stateless, no DB call).

        Args:
            token: The signed JWT string.

        Returns:
            Dict with tenant_id, catalog_ids, and jti.

        Raises:
            InvalidBuyerLinkError: If token is invalid.
            BuyerLinkExpiredError: If token has expired.
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_exp": True, "verify_aud": False},
                algorithms=[BUYER_LINK_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise BuyerLinkExpiredError("Buyer link has expired")
        except (jwt.JWTError, jwt.JWTClaimsError):
            raise InvalidBuyerLinkError("Invalid buyer link token")

        if payload.get("type") != "buyer_link":
            raise InvalidBuyerLinkError("Invalid buyer link token")

        return {
            "tenant_id": uuid.UUID(payload["sub"]),
            "catalog_ids": [uuid.UUID(cid) for cid in payload["catalog_ids"]],
            "jti": payload["jti"],
        }

    async def validate_link_with_tenant(self, token: str) -> dict:
        """Validate a buyer link and verify tenant is active.

        This adds a DB call to verify the tenant, but the core
        token validation is still stateless.

        Args:
            token: The signed JWT string.

        Returns:
            Dict with tenant_id, catalog_ids, jti, and tenant.

        Raises:
            InvalidBuyerLinkError: If token is invalid.
            BuyerLinkExpiredError: If token has expired.
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
        """
        result = self.validate_link(token)

        tenant = await self._tenant_repo.get_by_id(result["tenant_id"])
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        if not tenant.is_active:
            raise TenantInactiveError("Tenant is not active")

        result["tenant"] = tenant
        return result

    async def list_links(self, tenant_id: uuid.UUID) -> list[BuyerLink]:
        """List all buyer links for a tenant.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        return await self._buyer_link_repo.list_by_tenant(tenant_id)
