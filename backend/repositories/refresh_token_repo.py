"""Repository for RefreshToken persistence.

Enhanced operations for token rotation, bulk revocation, and denylist integration.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Data access for RefreshToken entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, mayorista_id: uuid.UUID, jti: str, expires_at: datetime
    ) -> RefreshToken:
        """Create a new refresh token."""
        token = RefreshToken(
            mayorista_id=mayorista_id,
            jti=jti,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        """Find a refresh token by its JTI."""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )
        return result.scalar_one_or_none()

    async def get_active_by_mayorista(
        self, mayorista_id: uuid.UUID
    ) -> list[RefreshToken]:
        """Get all non-revoked refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.mayorista_id == mayorista_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return list(result.scalars().all())

    async def revoke(self, jti: str) -> RefreshToken | None:
        """Revoke a single refresh token by JTI."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(revoked=True)
            .returning(RefreshToken)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def revoke_all(
        self, mayorista_id: uuid.UUID
    ) -> list[RefreshToken]:
        """Revoke all active refresh tokens for a user.

        Returns the list of revoked tokens (for denylist population).
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.mayorista_id == mayorista_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
            .returning(RefreshToken)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return list(result.scalars().all())
