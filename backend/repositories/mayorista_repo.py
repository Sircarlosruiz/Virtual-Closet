import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.mayorista import Mayorista
from models.refresh_token import RefreshToken


class MayoristaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Mayorista | None:
        result = await self.session.execute(select(Mayorista).where(Mayorista.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, mayorista_id: uuid.UUID) -> Mayorista | None:
        result = await self.session.execute(
            select(Mayorista).where(Mayorista.id == mayorista_id)
        )
        return result.scalar_one_or_none()

    async def create(self, mayorista: Mayorista) -> Mayorista:
        self.session.add(mayorista)
        await self.session.commit()
        await self.session.refresh(mayorista)
        return mayorista

    async def increment_failed_attempts(
        self, user_id: uuid.UUID
    ) -> tuple[int, bool] | None:
        """Atomically increment failed_attempts and lock if threshold reached.

        Returns (failed_attempts, is_locked) or None if user not found.
        Uses PostgreSQL atomic UPDATE to prevent race conditions under concurrent logins.
        """
        lock_threshold = 5
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == user_id)
            .values(
                failed_attempts=Mayorista.failed_attempts + 1,
                is_locked=(Mayorista.failed_attempts + 1 >= lock_threshold),
            )
            .returning(Mayorista.failed_attempts, Mayorista.is_locked)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        row = result.first()
        if row is None:
            return None
        return row.failed_attempts, row.is_locked

    async def reset_failed_attempts(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == user_id)
            .values(failed_attempts=0)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def lock_account(self, user_id: uuid.UUID) -> Mayorista | None:
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == user_id)
            .values(is_locked=True)
            .returning(Mayorista)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def unlock_account(self, user_id: uuid.UUID) -> Mayorista | None:
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == user_id)
            .values(is_locked=False, failed_attempts=0)
            .returning(Mayorista)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def mark_email_verified(self, user_id: uuid.UUID) -> Mayorista | None:
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == user_id)
            .values(email_verified=True)
            .returning(Mayorista)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_role(
        self, mayorista_id: uuid.UUID, new_role: str
    ) -> Mayorista | None:
        stmt = (
            update(Mayorista)
            .where(Mayorista.id == mayorista_id)
            .values(role=new_role)
            .returning(Mayorista)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def list_admins_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[Mayorista]:
        result = await self.session.execute(
            select(Mayorista)
            .where(
                Mayorista.tenant_id == tenant_id,
                Mayorista.role == "admin",
            )
            .order_by(Mayorista.created_at)
        )
        return list(result.scalars().all())

    async def create_refresh_token(
        self, mayorista_id: uuid.UUID, jti: str, expires_at
    ) -> RefreshToken:
        token = RefreshToken(
            mayorista_id=mayorista_id,
            jti=jti,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_active_refresh_tokens(
        self, mayorista_id: uuid.UUID
    ) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.mayorista_id == mayorista_id,
                RefreshToken.revoked.is_(False),
            )
        )
        return list(result.scalars().all())

    async def revoke_refresh_token(self, jti: str) -> RefreshToken | None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(revoked=True)
            .returning(RefreshToken)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def revoke_all_refresh_tokens(
        self, mayorista_id: uuid.UUID
    ) -> list[RefreshToken]:
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
