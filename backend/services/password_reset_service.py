"""Password reset service.

Handles password reset request, token validation, and completion
with session revocation.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from core.security import hash_password
from repositories.mayorista_repo import MayoristaRepository
from repositories.password_reset_token_repo import PasswordResetTokenRepository
from services.session_service import SessionService

logger = logging.getLogger(__name__)

# ── Domain Exceptions ──────────────────────────────────────────────────────


class InvalidResetTokenError(Exception):
    """Raised when the reset token is invalid."""


class ExpiredResetTokenError(Exception):
    """Raised when the reset token has expired."""


class UsedResetTokenError(Exception):
    """Raised when the reset token has already been used."""


# ── Constants ──────────────────────────────────────────────────────────────

RESET_TOKEN_TTL_HOURS = 1


def _hash_token(token_value: str) -> str:
    """Hash a token value using SHA-256 for storage.

    SHA-256 is safe for lookup because tokens are random 64-char hex
    strings with 1-hour TTL (unpredictable and time-limited).
    """
    return hashlib.sha256(token_value.encode("utf-8")).hexdigest()


class PasswordResetService:
    """Domain service for password reset flows."""

    def __init__(
        self,
        mayorista_repo: MayoristaRepository,
        reset_token_repo: PasswordResetTokenRepository,
        session_service: SessionService | None = None,
    ):
        self.mayorista_repo = mayorista_repo
        self.reset_token_repo = reset_token_repo
        self.session_service = session_service

    async def request_reset(self, email: str) -> bool:
        """Request a password reset for the given email.

        Always returns True (no enumeration). If the email exists,
        generates a token, invalidates previous tokens, and sends email.
        """
        email = email.lower()
        mayorista = await self.mayorista_repo.get_by_email(email)

        if mayorista is None:
            return True

        # Invalidate all previous unused tokens
        await self.reset_token_repo.invalidate_all_unused(mayorista.id)

        # Generate new token
        from core.security import generate_verification_token

        token_value = generate_verification_token()
        token_hash = _hash_token(token_value)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)

        await self.reset_token_repo.create(
            mayorista_id=mayorista.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Send reset email
        from services.email_service import send_password_reset_email

        try:
            await send_password_reset_email(
                mayorista.email,
                mayorista.nombre_negocio,
                token_value,
            )
        except Exception:
            logger.exception("Failed to send password reset email to %s", email)

        return True

    async def validate_token(self, token_value: str):
        """Validate a password reset token.

        Returns the token entity if valid.

        Raises:
            ExpiredResetTokenError: If the token has expired.
            InvalidResetTokenError: If the token is not found.
        """
        token_hash = _hash_token(token_value)
        reset_token = await self.reset_token_repo.find_by_token_hash(token_hash)

        if reset_token is None:
            raise InvalidResetTokenError("Invalid reset token")

        if reset_token.used:
            raise UsedResetTokenError("Link already used, please request a new one")

        if reset_token.expires_at < datetime.now(timezone.utc):
            raise ExpiredResetTokenError("Link expired, please request a new one")

        return reset_token

    async def complete_reset(
        self, token_value: str, new_password: str
    ) -> UUID:
        """Complete a password reset.

        Validates the token, updates the password, and revokes all sessions.

        Returns the mayorista_id.

        Raises:
            InvalidResetTokenError: If the token is invalid.
            ExpiredResetTokenError: If the token has expired.
            UsedResetTokenError: If the token has already been used.
        """
        reset_token = await self.validate_token(token_value)

        # Update password
        new_hash = hash_password(new_password)
        mayorista = await self.mayorista_repo.get_by_id(reset_token.mayorista_id)
        if mayorista is None:
            raise InvalidResetTokenError("Invalid reset token")

        from sqlalchemy import update
        from models.mayorista import Mayorista

        await self.reset_token_repo.session.execute(
            update(Mayorista)
            .where(Mayorista.id == mayorista.id)
            .values(password_hash=new_hash)
        )
        await self.reset_token_repo.session.commit()

        # Mark token as used
        await self.reset_token_repo.mark_used(reset_token)

        # Revoke all sessions (ADR-029)
        if self.session_service:
            revoked_count = await self.session_service.revoke_sessions_by_mayorista(
                mayorista.id
            )
            logger.info(
                "Password reset for user %s: %d sessions revoked",
                mayorista.id,
                revoked_count,
            )

        return mayorista.id
