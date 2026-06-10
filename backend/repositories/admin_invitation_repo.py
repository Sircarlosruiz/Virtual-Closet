"""Data access for AdminInvitation entities."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.admin_invitation import AdminInvitation


class AdminInvitationRepo:
    """Data access for AdminInvitation entities."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, invitation: AdminInvitation) -> AdminInvitation:
        self._db.add(invitation)
        await self._db.commit()
        await self._db.refresh(invitation)
        return invitation

    async def get_by_token(self, token: str) -> AdminInvitation | None:
        result = await self._db.execute(
            select(AdminInvitation).where(AdminInvitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_pending_by_email_and_tenant(
        self, email: str, tenant_id: uuid.UUID
    ) -> AdminInvitation | None:
        result = await self._db.execute(
            select(AdminInvitation).where(
                AdminInvitation.email == email,
                AdminInvitation.tenant_id == tenant_id,
                AdminInvitation.accepted.is_(False),
                AdminInvitation.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[AdminInvitation]:
        result = await self._db.execute(
            select(AdminInvitation)
            .where(AdminInvitation.tenant_id == tenant_id)
            .order_by(AdminInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_pending_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[AdminInvitation]:
        result = await self._db.execute(
            select(AdminInvitation)
            .where(
                AdminInvitation.tenant_id == tenant_id,
                AdminInvitation.accepted.is_(False),
            )
            .order_by(AdminInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_accepted(self, invitation_id: uuid.UUID) -> AdminInvitation | None:
        stmt = (
            update(AdminInvitation)
            .where(AdminInvitation.id == invitation_id)
            .values(accepted=True)
            .returning(AdminInvitation)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one_or_none()

    async def expire_old_invitations(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            update(AdminInvitation)
            .where(
                AdminInvitation.tenant_id == tenant_id,
                AdminInvitation.accepted.is_(False),
                AdminInvitation.expires_at < datetime.now(timezone.utc),
            )
            .values(accepted=True)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount
