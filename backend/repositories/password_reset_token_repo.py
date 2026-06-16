"""Repository for PasswordResetToken persistence."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """Data access for PasswordResetToken entities.

    Tokens are stored as SHA-256 hashes for lookup (safe because tokens
    are random 64-char hex strings with 1-hour TTL).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, mayorista_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        """Create a new password reset token.

        token_hash should be a SHA-256 hex digest of the raw token value.
        """
        token = PasswordResetToken(
            mayorista_id=mayorista_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def find_by_token_hash(
        self, token_hash: str
    ) -> PasswordResetToken | None:
        """Find a reset token by its SHA-256 hash."""
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_all_unused(
        self, mayorista_id: uuid.UUID
    ) -> int:
        """Mark all unused tokens as used (invalidated by new request).

        Returns the count of invalidated tokens.
        """
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.mayorista_id == mayorista_id,
                PasswordResetToken.used.is_(False),
            )
            .values(
                used=True,
                used_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def mark_used(self, token: PasswordResetToken) -> None:
        """Mark a reset token as used."""
        token.used = True
        token.used_at = datetime.now(timezone.utc)
        await self.session.commit()
