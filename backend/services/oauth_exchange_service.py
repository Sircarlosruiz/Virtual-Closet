"""OAuth exchange service.

Handles Google OAuth session exchange for challenge_token issuance.
Implements account linking security (ADR-024).
"""

import logging
import secrets
from uuid import UUID

from core.security import (
    create_challenge_token,
    hash_password,
    verify_password,
)
from core.security import decrypt_value
from models.oauth import OAuthLink
from models.mayorista import Mayorista
from models.tenant import Tenant
from repositories.mayorista_repo import MayoristaRepository
from repositories.oauth_link_repo import OAuthLinkRepository
from repositories.tenant_repo import TenantRepo
from repositories.two_factor_config_repo import TwoFactorConfigRepository

logger = logging.getLogger(__name__)

# ── Domain Exceptions ──────────────────────────────────────────────────────


class OAuthTokenInvalidError(Exception):
    """Raised when the NextAuth session token is invalid."""


class AccountLinkingRequiredError(Exception):
    """Raised when Google email matches an existing email+password account."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Account linking required for {email}")


class AccountLinkingRejectedError(Exception):
    """Raised when the user rejects account linking."""


class OAuthExchangeError(Exception):
    """Raised when OAuth exchange fails for any reason."""


class OAuthExchangeService:
    """Domain service for Google OAuth exchange flows."""

    def __init__(
        self,
        mayorista_repo: MayoristaRepository,
        oauth_link_repo: OAuthLinkRepository,
        two_factor_repo: TwoFactorConfigRepository,
        tenant_repo: TenantRepo | None = None,
    ):
        self.mayorista_repo = mayorista_repo
        self.oauth_link_repo = oauth_link_repo
        self.two_factor_repo = two_factor_repo
        self.tenant_repo = tenant_repo

    async def exchange(
        self,
        provider: str,
        provider_sub: str,
        provider_email: str,
    ) -> dict:
        """Exchange a Google OAuth identity for a challenge_token.

        Flow:
        1. Check if provider_sub is already linked → return challenge_token
        2. Check if email matches existing account → require account linking
        3. Create new user + tenant → return challenge_token

        Returns dict with challenge_token and flow instructions.
        """
        # Step 1: Check if already linked
        existing_link = await self.oauth_link_repo.get_by_provider_sub(
            provider, provider_sub
        )
        if existing_link:
            mayorista = await self.mayorista_repo.get_by_id(existing_link.mayorista_id)
            if mayorista is None:
                raise OAuthExchangeError("Linked account not found")

            challenge_token = create_challenge_token(str(mayorista.id))
            requires_2fa_setup = not await self._is_2fa_configured(mayorista.id)

            return {
                "challenge_token": challenge_token,
                "requires_2fa_setup": requires_2fa_setup,
                "requires_2fa_challenge": not requires_2fa_setup,
                "user": mayorista,
            }

        # Step 2: Check if email matches existing account
        existing_user = await self.mayorista_repo.get_by_email(provider_email.lower())
        if existing_user:
            raise AccountLinkingRequiredError(provider_email)

        # Step 3: Create new user + tenant
        mayorista, tenant = await self._create_oauth_user(
            email=provider_email,
            provider=provider,
            provider_sub=provider_sub,
        )

        challenge_token = create_challenge_token(str(mayorista.id))

        return {
            "challenge_token": challenge_token,
            "requires_2fa_setup": True,
            "requires_business_name": True,
            "user": mayorista,
        }

    async def link_account(
        self,
        mayorista_id: UUID,
        password: str,
        provider: str,
        provider_sub: str,
        provider_email: str,
    ) -> dict:
        """Link a Google OAuth identity to an existing email+password account.

        Requires password confirmation (ADR-024).

        Raises:
            InvalidCredentialsError: If password is incorrect.
        """
        mayorista = await self.mayorista_repo.get_by_id(mayorista_id)
        if mayorista is None:
            raise OAuthExchangeError("Account not found")

        if not verify_password(password, mayorista.password_hash):
            from services.auth_service import InvalidCredentialsError

            raise InvalidCredentialsError("Password incorrect")

        # Create the OAuth link
        await self.oauth_link_repo.link_to_existing(
            mayorista_id=mayorista_id,
            provider=provider,
            provider_sub=provider_sub,
            provider_email=provider_email,
        )

        challenge_token = create_challenge_token(str(mayorista_id))
        requires_2fa_setup = not await self._is_2fa_configured(mayorista_id)

        return {
            "challenge_token": challenge_token,
            "requires_2fa_setup": requires_2fa_setup,
            "requires_2fa_challenge": not requires_2fa_setup,
            "linked": True,
        }

    async def _create_oauth_user(
        self,
        email: str,
        provider: str,
        provider_sub: str,
    ) -> tuple[Mayorista, Tenant]:
        """Create a new mayorista and tenant for a Google OAuth user.

        Email is pre-verified (Google handles verification).
        """
        email = email.lower()

        # Create tenant
        tenant_slug = self._generate_tenant_slug(email)
        tenant = Tenant(
            name=email.split("@")[0],
            slug=tenant_slug,
            buyer_link_secret=secrets.token_hex(32),
        )
        if self.tenant_repo:
            tenant = await self.tenant_repo.create(tenant)
        else:
            self.mayorista_repo.session.add(tenant)
            await self.mayorista_repo.session.commit()
            await self.mayorista_repo.session.refresh(tenant)

        # Create user with random password (OAuth-only, no password login)
        random_password = secrets.token_hex(32)
        mayorista = Mayorista(
            email=email,
            password_hash=hash_password(random_password),
            nombre_negocio=email.split("@")[0],
            tenant_id=tenant.id,
            email_verified=True,  # Google handles verification
            is_locked=False,
            failed_attempts=0,
        )
        mayorista = await self.mayorista_repo.create(mayorista)

        # Create OAuth link
        await self.oauth_link_repo.link_to_existing(
            mayorista_id=mayorista.id,
            provider=provider,
            provider_sub=provider_sub,
            provider_email=email,
        )

        return mayorista, tenant

    async def _is_2fa_configured(self, mayorista_id: UUID) -> bool:
        """Check if 2FA is configured for a user."""
        config = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        return config is not None and config.is_configured

    @staticmethod
    def _generate_tenant_slug(email: str) -> str:
        """Generate a URL-safe slug from email for tenant."""
        import re

        local_part = email.split("@")[0]
        slug = re.sub(r"[^a-z0-9]+", "-", local_part.lower().strip()).strip("-")
        slug = slug[:40]
        suffix = secrets.token_hex(2)
        return f"{slug}-{suffix}"
