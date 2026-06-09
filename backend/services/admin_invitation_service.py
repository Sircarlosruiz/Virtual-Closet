"""Admin invitation service for tenant admin management."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from core.config import settings
from repositories.admin_invitation_repo import AdminInvitationRepo
from repositories.tenant_repo import TenantRepo
from models.admin_invitation import AdminInvitation
from models.tenant import Tenant
from services.email_service import send_invitation_email
from services.tenant_service import TenantNotFoundError, TenantInactiveError


class InvitationExpiredError(Exception):
    """Invitation token has expired."""


class InvitationAlreadyAcceptedError(Exception):
    """Invitation has already been accepted."""


class PendingInvitationExistsError(Exception):
    """A pending invitation already exists for this email."""


class AdminInvitationService:
    """Handles admin invitation lifecycle."""

    INVITATION_TTL_DAYS = 7

    def __init__(
        self,
        invitation_repo: AdminInvitationRepo,
        tenant_repo: TenantRepo,
    ) -> None:
        self._invitation_repo = invitation_repo
        self._tenant_repo = tenant_repo

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_hex(64)

    async def invite_admin(
        self,
        tenant_id: uuid.UUID,
        email: str,
        created_by: uuid.UUID,
    ) -> AdminInvitation:
        """Create a new admin invitation.

        Args:
            tenant_id: The tenant to invite the admin to.
            email: Email address of the invitee.
            created_by: UUID of the user creating the invitation.

        Returns:
            The created AdminInvitation.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
            PendingInvitationExistsError: If a pending invitation exists for this email.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")
        if not tenant.is_active:
            raise TenantInactiveError("Tenant is not active")

        existing = await self._invitation_repo.get_pending_by_email_and_tenant(
            email, tenant_id
        )
        if existing is not None:
            raise PendingInvitationExistsError(
                f"A pending invitation already exists for {email}"
            )

        token = self._generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.INVITATION_TTL_DAYS
        )

        invitation = AdminInvitation(
            tenant_id=tenant_id,
            email=email,
            token=token,
            expires_at=expires_at,
            created_by=created_by,
        )
        return await self._invitation_repo.create(invitation)

    async def get_invitation(self, token: str) -> AdminInvitation:
        """Get an invitation by token and validate it.

        Args:
            token: The invitation token.

        Returns:
            The valid AdminInvitation.

        Raises:
            TenantNotFoundError: If invitation does not exist.
            InvitationExpiredError: If invitation has expired.
            InvitationAlreadyAcceptedError: If invitation has been accepted.
        """
        invitation = await self._invitation_repo.get_by_token(token)
        if invitation is None:
            raise TenantNotFoundError("Invitation not found")

        if invitation.accepted:
            raise InvitationAlreadyAcceptedError(
                "This invitation has already been accepted"
            )

        if invitation.expires_at < datetime.now(timezone.utc):
            raise InvitationExpiredError(
                "This invitation has expired"
            )

        return invitation

    async def accept_invitation(self, token: str) -> AdminInvitation:
        """Mark an invitation as accepted.

        Args:
            token: The invitation token.

        Returns:
            The accepted AdminInvitation.

        Raises:
            TenantNotFoundError: If invitation does not exist.
            InvitationExpiredError: If invitation has expired.
            InvitationAlreadyAcceptedError: If invitation has been accepted.
        """
        invitation = await self.get_invitation(token)
        return await self._invitation_repo.mark_accepted(invitation.id)

    async def list_invitations(
        self, tenant_id: uuid.UUID
    ) -> list[AdminInvitation]:
        """List all invitations for a tenant.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        return await self._invitation_repo.list_by_tenant(tenant_id)

    async def list_pending_invitations(
        self, tenant_id: uuid.UUID
    ) -> list[AdminInvitation]:
        """List pending (unaccepted) invitations for a tenant.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        return await self._invitation_repo.list_pending_by_tenant(tenant_id)
