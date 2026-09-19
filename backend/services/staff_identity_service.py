"""Provision, revoke, and resolve BFashion staff mirrors (ADR-057, ADR-058)."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from models.mayorista import Mayorista
from models.service_client import ServiceClient
from models.staff_identity_link import StaffIdentityLink
from repositories.mayorista_repo import MayoristaRepository
from repositories.staff_identity_link_repo import StaffIdentityLinkRepository

logger = logging.getLogger(__name__)


def _staff_roles() -> set[str]:
    # Imported lazily to avoid a cycle: integration → product_link → staff_identity.
    from services.integration_service import STAFF_ROLES

    return STAFF_ROLES


class StaffIdentityError(Exception):
    """Base error for staff-identity operations."""

    code = "STAFF_IDENTITY_ERROR"
    status_code = 400

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class StaffForbiddenError(StaffIdentityError):
    """Asserted staff_id is unknown, wrong tenant, wrong role, or revoked."""

    code = "STAFF_FORBIDDEN"
    status_code = 403


class StaffIdentityNotFoundError(StaffIdentityError):
    """external_staff_id is unknown in this service client's scope."""

    code = "STAFF_IDENTITY_NOT_FOUND"
    status_code = 404


class MirrorEmailConflictError(StaffIdentityError):
    """Email already belongs to a real mayorista or another mirror."""

    code = "STAFF_EMAIL_CONFLICT"
    status_code = 409


class StaffIdentityResult:
    def __init__(
        self,
        link: StaffIdentityLink,
        mayorista: Mayorista,
        created: bool,
    ) -> None:
        self.link = link
        self.mayorista = mayorista
        self.created = created


class StaffIdentityService:
    def __init__(
        self,
        db: AsyncSession,
        links: StaffIdentityLinkRepository,
        mayoristas: MayoristaRepository,
    ) -> None:
        self._db = db
        self._links = links
        self._mayoristas = mayoristas

    async def resolve_staff_identity(
        self, client: ServiceClient, staff_id: UUID
    ) -> Mayorista:
        """Contract-C staff gate (ADR-057). Does not call ``_authorize_staff``."""
        staff = await self._mayoristas.get_by_id(staff_id)
        if staff is None or staff.role not in _staff_roles():
            raise StaffForbiddenError("Staff access required")
        if staff.tenant_id is None or staff.tenant_id != client.tenant_id:
            raise StaffForbiddenError("Staff actor does not belong to this tenant")

        link = await self._links.get_active_by_mayorista(
            client.system, client.tenant_id, staff.id
        )
        if link is None:
            raise StaffForbiddenError("Staff identity is not active")
        return staff

    async def provision(
        self,
        client: ServiceClient,
        external_staff_id: str,
        email: str,
        display_name: str,
        role: str,
    ) -> StaffIdentityResult:
        if role not in _staff_roles():
            raise StaffIdentityError(
                "role must be one of admin, owner, staff",
                context={"role": role},
            )

        existing = await self._links.get_by_system_and_external_staff(
            client.system, external_staff_id
        )
        if existing is not None:
            return await self._replay_or_reactivate(client, existing)

        holder = await self._mayoristas.get_by_email(email)
        if holder is not None:
            raise MirrorEmailConflictError(
                "Email already belongs to another mayorista",
                context={"email": email},
            )

        try:
            mayorista = Mayorista(
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                nombre_negocio=display_name,
                tenant_id=client.tenant_id,
                role=role,
            )
            await self._mayoristas.add(mayorista)
            link = StaffIdentityLink(
                system=client.system,
                external_staff_id=external_staff_id,
                mayorista_id=mayorista.id,
                tenant_id=client.tenant_id,
                is_active=True,
            )
            await self._links.add(link)
            await self._db.commit()
            await self._db.refresh(link)
            await self._db.refresh(mayorista)
        except IntegrityError:
            await self._db.rollback()
            raced = await self._links.get_by_system_and_external_staff(
                client.system, external_staff_id
            )
            if raced is not None:
                return await self._replay_or_reactivate(client, raced)
            if await self._mayoristas.get_by_email(email) is not None:
                raise MirrorEmailConflictError(
                    "Email already belongs to another mayorista",
                    context={"email": email},
                ) from None
            raise

        logger.info(
            "staff_identity_provisioned",
            extra={
                "staff_id": str(mayorista.id),
                "external_staff_id": external_staff_id,
                "system": client.system,
                "tenant_id": str(client.tenant_id),
                "link_created": True,
            },
        )
        return StaffIdentityResult(link, mayorista, created=True)

    async def revoke(
        self, client: ServiceClient, external_staff_id: str
    ) -> StaffIdentityResult:
        link = await self._links.get_by_system_and_external_staff(
            client.system, external_staff_id
        )
        if link is None or link.tenant_id != client.tenant_id:
            raise StaffIdentityNotFoundError("Staff identity not found")

        if not link.is_active:
            mayorista = await self._mayoristas.get_by_id(link.mayorista_id)
            if mayorista is None:
                raise StaffIdentityNotFoundError("Staff identity not found")
            return StaffIdentityResult(link, mayorista, created=False)

        link.is_active = False
        link.revoked_at = datetime.now(timezone.utc)
        await self._links.save(link)
        await self._db.commit()
        await self._db.refresh(link)
        mayorista = await self._mayoristas.get_by_id(link.mayorista_id)
        if mayorista is None:
            raise StaffIdentityNotFoundError("Staff identity not found")

        logger.info(
            "staff_identity_revoked",
            extra={
                "staff_id": str(link.mayorista_id),
                "external_staff_id": external_staff_id,
                "system": client.system,
                "tenant_id": str(client.tenant_id),
            },
        )
        return StaffIdentityResult(link, mayorista, created=False)

    async def _replay_or_reactivate(
        self, client: ServiceClient, link: StaffIdentityLink
    ) -> StaffIdentityResult:
        if link.tenant_id != client.tenant_id:
            raise StaffForbiddenError("Staff identity belongs to a different tenant")

        mayorista = await self._mayoristas.get_by_id(link.mayorista_id)
        if mayorista is None:
            raise StaffIdentityNotFoundError("Staff identity not found")

        if link.is_active:
            logger.info(
                "staff_identity_replayed",
                extra={
                    "staff_id": str(link.mayorista_id),
                    "external_staff_id": link.external_staff_id,
                    "system": client.system,
                    "link_created": False,
                },
            )
            return StaffIdentityResult(link, mayorista, created=False)

        link.is_active = True
        link.revoked_at = None
        await self._links.save(link)
        await self._db.commit()
        await self._db.refresh(link)
        logger.info(
            "staff_identity_reactivated",
            extra={
                "staff_id": str(link.mayorista_id),
                "external_staff_id": link.external_staff_id,
                "system": client.system,
                "link_created": False,
            },
        )
        return StaffIdentityResult(link, mayorista, created=False)
