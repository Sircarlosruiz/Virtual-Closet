"""Repository for TwoFactorConfig persistence."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.two_factor import TwoFactorConfig


class TwoFactorConfigRepository:
    """Data access for TwoFactorConfig entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_mayorista_id(
        self, mayorista_id: uuid.UUID
    ) -> TwoFactorConfig | None:
        """Get 2FA config for a user, or None if not found."""
        result = await self.session.execute(
            select(TwoFactorConfig).where(
                TwoFactorConfig.mayorista_id == mayorista_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, config: TwoFactorConfig) -> TwoFactorConfig:
        """Persist a new TwoFactorConfig."""
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def update(self, config: TwoFactorConfig) -> TwoFactorConfig:
        """Update an existing TwoFactorConfig."""
        await self.session.merge(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def mark_configured(
        self, mayorista_id: uuid.UUID, method: str
    ) -> TwoFactorConfig | None:
        """Mark 2FA as configured for the given method."""
        stmt = (
            update(TwoFactorConfig)
            .where(TwoFactorConfig.mayorista_id == mayorista_id)
            .values(
                is_configured=True,
                method=method,
                backup_codes_remaining=8,
            )
            .returning(TwoFactorConfig)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def decrement_backup_codes(
        self, mayorista_id: uuid.UUID
    ) -> int | None:
        """Decrement backup_codes_remaining by 1. Returns new count or None."""
        stmt = (
            update(TwoFactorConfig)
            .where(TwoFactorConfig.mayorista_id == mayorista_id)
            .values(
                backup_codes_remaining=TwoFactorConfig.backup_codes_remaining - 1
            )
            .returning(TwoFactorConfig.backup_codes_remaining)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.first()
        return row.backup_codes_remaining if row else None
