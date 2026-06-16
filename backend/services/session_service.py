"""Session service for JWT lifecycle management.

Handles session issuance after 2FA, refresh token rotation,
and session revocation (single-device and all-devices).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from core.config import settings
from core.security import create_rs256_access_token, decode_rs256_access_token
from repositories.refresh_token_repo import RefreshTokenRepository
from services.redis_denylist_service import RedisDenylistService, RedisUnavailableError

logger = logging.getLogger(__name__)

# ── Domain Exceptions ──────────────────────────────────────────────────────


class InvalidRefreshTokenError(Exception):
    """Raised when the refresh token is invalid, expired, or revoked."""


class SessionExpiredError(Exception):
    """Raised when the session has expired and cannot be refreshed."""


# ── Constants ──────────────────────────────────────────────────────────────

ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 7


class SessionService:
    """Domain service for JWT session lifecycle."""

    def __init__(
        self,
        refresh_token_repo: RefreshTokenRepository,
        denylist_service: RedisDenylistService | None = None,
    ):
        self.refresh_token_repo = refresh_token_repo
        self.denylist_service = denylist_service or RedisDenylistService()

    async def issue_session(
        self, mayorista_id: UUID, tenant_id: UUID, role: str
    ) -> dict:
        """Issue a new JWT session after 2FA completion.

        Returns access_token (RS256 JWT), refresh_token (opaque), and metadata.
        """
        # Generate access token
        access_token, access_jti = create_rs256_access_token(
            mayorista_id=str(mayorista_id),
            tenant_id=str(tenant_id),
            role=role,
            expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        )

        # Generate refresh token
        refresh_jti = str(uuid.uuid4())
        refresh_expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)

        refresh_token = await self.refresh_token_repo.create(
            mayorista_id=mayorista_id,
            jti=refresh_jti,
            expires_at=refresh_expires,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_jti,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL_MINUTES * 60,
            "refresh_expires_at": refresh_expires.isoformat(),
        }

    async def refresh_session(self, refresh_token_jti: str) -> dict:
        """Rotate refresh token: issue new access + refresh tokens.

        Implements immediate denylist on rotation (ADR-028).
        Fails closed if Redis is unavailable (ADR-027).

        Raises:
            InvalidRefreshTokenError: If token is invalid, expired, or revoked.
            RedisUnavailableError: If Redis denylist is unavailable.
        """
        # 1. Look up the refresh token
        token = await self.refresh_token_repo.get_by_jti(refresh_token_jti)
        if token is None:
            raise InvalidRefreshTokenError("Session expired, please log in again")

        # 2. Check if revoked
        if token.revoked:
            raise InvalidRefreshTokenError("Session expired, please log in again")

        # 3. Check if expired
        if token.expires_at < datetime.now(timezone.utc):
            await self.refresh_token_repo.revoke(refresh_token_jti)
            raise InvalidRefreshTokenError("Session expired, please log in again")

        # 4. Add old JTI to denylist BEFORE issuing new tokens (ADR-028)
        remaining_ttl = int((token.expires_at - datetime.now(timezone.utc)).total_seconds())
        added = await self.denylist_service.add(refresh_token_jti, max(remaining_ttl, 0))

        if not added:
            # Token already in denylist — concurrent refresh detected
            raise InvalidRefreshTokenError("Session expired, please log in again")

        # 5. Revoke old token in DB
        await self.refresh_token_repo.revoke(refresh_token_jti)

        # 6. Issue new tokens
        return await self.issue_session(
            mayorista_id=token.mayorista_id,
            tenant_id=UUID(str(token.mayorista_id)),  # TODO: fetch tenant_id from mayorista
            role="mayorista",  # TODO: fetch role from mayorista
        )

    async def revoke_session(self, jti: str) -> bool:
        """Revoke a single refresh token (single-device logout).

        Adds JTI to denylist and marks as revoked in DB.
        """
        token = await self.refresh_token_repo.get_by_jti(jti)
        if token is None:
            return False

        await self.refresh_token_repo.revoke(jti)

        remaining_ttl = int((token.expires_at - datetime.now(timezone.utc)).total_seconds())
        await self.denylist_service.add(jti, max(remaining_ttl, 0))

        return True

    async def revoke_all_sessions(self, mayorista_id: UUID) -> int:
        """Revoke all active refresh tokens for a user (all-devices logout).

        Returns the count of revoked tokens.
        """
        revoked_tokens = await self.refresh_token_repo.revoke_all(mayorista_id)

        # Add all JTIs to denylist
        now = datetime.now(timezone.utc)
        jti_list = []
        for token in revoked_tokens:
            if token.expires_at > now:
                remaining_ttl = int((token.expires_at - now).total_seconds())
                jti_list.append((token.jti, remaining_ttl))

        if jti_list:
            for jti, ttl in jti_list:
                await self.denylist_service.add(jti, max(ttl, 0))

        return len(revoked_tokens)

    async def revoke_sessions_by_mayorista(self, mayorista_id: UUID) -> int:
        """Revoke all sessions for a mayorista (used by password reset).

        Same as revoke_all_sessions but with explicit naming for clarity.
        """
        return await self.revoke_all_sessions(mayorista_id)
