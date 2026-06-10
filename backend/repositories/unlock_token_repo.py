"""Repository for unlock tokens."""

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.unlock_token import UnlockToken


class UnlockTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, token: UnlockToken) -> UnlockToken:
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def find_by_token(self, token: str) -> UnlockToken | None:
        result = await self.session.execute(
            select(UnlockToken).where(UnlockToken.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: str) -> UnlockToken | None:
        stmt = (
            update(UnlockToken)
            .where(UnlockToken.token == token)
            .values(used=True)
            .returning(UnlockToken)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete_expired(self) -> int:
        from datetime import datetime, timezone

        stmt = delete(UnlockToken).where(
            UnlockToken.expires_at < datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
