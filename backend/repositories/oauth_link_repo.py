"""Repository for OAuthLink persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.oauth import OAuthLink


class OAuthLinkRepository:
    """Data access for OAuthLink entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_provider_sub(
        self, provider: str, provider_sub: str
    ) -> OAuthLink | None:
        """Find an OAuth link by provider and subject ID."""
        result = await self.session.execute(
            select(OAuthLink).where(
                OAuthLink.provider == provider,
                OAuthLink.provider_sub == provider_sub,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_mayorista_id(
        self, mayorista_id: uuid.UUID
    ) -> OAuthLink | None:
        """Find an OAuth link for a user."""
        result = await self.session.execute(
            select(OAuthLink).where(
                OAuthLink.mayorista_id == mayorista_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, link: OAuthLink) -> OAuthLink:
        """Persist a new OAuth link."""
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def link_to_existing(
        self, mayorista_id: uuid.UUID, provider: str, provider_sub: str, provider_email: str
    ) -> OAuthLink:
        """Link an OAuth identity to an existing mayorista account."""
        link = OAuthLink(
            mayorista_id=mayorista_id,
            provider=provider,
            provider_sub=provider_sub,
            provider_email=provider_email,
        )
        return await self.create(link)
