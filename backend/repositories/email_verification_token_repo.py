"""Repository for email verification tokens."""

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.email_verification_token import EmailVerificationToken


class EmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def find_by_token(self, token: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        )
        return result.scalar_one_or_none()

    async def invalidate_by_user_id(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used.is_(False),
            )
            .values(used=True)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def mark_used(self, token: str) -> EmailVerificationToken | None:
        stmt = (
            update(EmailVerificationToken)
            .where(EmailVerificationToken.token == token)
            .values(used=True)
            .returning(EmailVerificationToken)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_expired(self) -> int:
        from datetime import datetime, timezone

        stmt = delete(EmailVerificationToken).where(
            EmailVerificationToken.expires_at < datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
