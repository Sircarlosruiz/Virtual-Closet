from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.mayorista import Mayorista


class MayoristaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Mayorista | None:
        result = await self.session.execute(select(Mayorista).where(Mayorista.email == email))
        return result.scalar_one_or_none()

    async def create(self, mayorista: Mayorista) -> Mayorista:
        self.session.add(mayorista)
        await self.session.commit()
        await self.session.refresh(mayorista)
        return mayorista
