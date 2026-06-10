"""Admin invitation service for tenant admin management."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from core.redis_client import get_redis
from repositories.admin_invitation_repo import AdminInvitationRepo
from repositories.mayorista_repo import MayoristaRepository
from repositories.tenant_repo import TenantRepo
from models.admin_invitation import AdminInvitation
from models.mayorista import Mayorista
from services.email_service import send_admin_invitation_email
from services.tenant_service import TenantNotFoundError, TenantInactiveError


logger = logging.getLogger(__name__)


class InvitationExpiredError(Exception):
    """Invitation token has expired."""


class InvitationAlreadyAcceptedError(Exception):
    """Invitation has already been accepted."""


class PendingInvitationExistsError(Exception):
    """A pending invitation already exists for this email."""


class AdminNotFoundError(Exception):
    """Admin user not found in tenant."""


class AdminRevocationError(Exception):
    """Cannot revoke this admin."""


class EmailAlreadyRegisteredError(Exception):
    """Email is already registered on the platform."""


class MaxInvitationsReachedError(Exception):
    """Maximum pending invitations reached for tenant."""


class AdminInvitationService:
    """Handles admin invitation lifecycle and admin management."""

    INVITATION_TTL_DAYS = 7
    MAX_PENDING_INVITATIONS = 10

    def __init__(
        self,
        invitation_repo: AdminInvitationRepo,
        tenant_repo: TenantRepo,
        mayorista_repo: MayoristaRepository,
    ) -> None:
        self._invitation_repo = invitation_repo
        self._tenant_repo = tenant_repo
        self._mayorista_repo = mayorista_repo

    @staticmethod
    def _generate_token() -> str:
        return secrets.token_hex(64)

    async def invite_admin(
        self,
        tenant_id: uuid.UUID,
        email: str,
        created_by: uuid.UUID,
        tenant_name: str = "",
    ) -> AdminInvitation:
        """Create a new admin invitation and send email.

        Args:
            tenant_id: The tenant to invite the admin to.
            email: Email address of the invitee.
            created_by: UUID of the user creating the invitation.
            tenant_name: Name of the tenant for the invitation email.

        Returns:
            The created AdminInvitation.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            TenantInactiveError: If tenant is not active.
            PendingInvitationExistsError: If a pending invitation exists for this email.
            MaxInvitationsReachedError: If max pending invitations reached.
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

        pending_count = len(
            await self._invitation_repo.list_pending_by_tenant(tenant_id)
        )
        if pending_count >= self.MAX_PENDING_INVITATIONS:
            raise MaxInvitationsReachedError(
                f"Maximum {self.MAX_PENDING_INVITATIONS} pending invitations reached"
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
        invitation = await self._invitation_repo.create(invitation)

        await send_admin_invitation_email(
            email=email,
            tenant_name=tenant_name,
            invitation_token=token,
        )

        return invitation

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

    async def list_admins(self, tenant_id: uuid.UUID) -> list[Mayorista]:
        """List all active admins in a tenant.

        Args:
            tenant_id: The tenant to list admins for.

        Returns:
            List of Mayorista users with role='admin'.

        Raises:
            TenantNotFoundError: If tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        return await self._mayorista_repo.list_admins_by_tenant(tenant_id)

    async def revoke_admin(
        self,
        tenant_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        revoked_by: uuid.UUID,
    ) -> int:
        """Revoke an admin's access and invalidate their sessions.

        Args:
            tenant_id: The tenant the admin belongs to.
            admin_user_id: The admin user to revoke.
            revoked_by: The user performing the revocation.

        Returns:
            Number of sessions invalidated.

        Raises:
            TenantNotFoundError: If tenant does not exist.
            AdminNotFoundError: If admin not found in tenant.
            AdminRevocationError: If cannot revoke (self-revoke or mayorista).
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant not found")

        if admin_user_id == revoked_by:
            raise AdminRevocationError(
                "Cannot revoke your own access"
            )

        admin = await self._mayorista_repo.get_by_id(admin_user_id)
        if admin is None:
            raise AdminNotFoundError("Admin user not found")

        if admin.tenant_id != tenant_id:
            raise AdminNotFoundError("Admin not found in this tenant")

        if admin.role == "mayorista":
            raise AdminRevocationError(
                "Cannot revoke the primary account owner"
            )

        revoked_tokens = await self._mayorista_repo.revoke_all_refresh_tokens(
            admin_user_id
        )

        await self._mayorista_repo.update_role(admin_user_id, "revoked")

        session_count = 0
        redis_client = await get_redis()
        if redis_client:
            for token in revoked_tokens:
                remaining_ttl = int(
                    (token.expires_at - datetime.now(timezone.utc)).total_seconds()
                )
                if remaining_ttl > 0:
                    try:
                        await redis_client.set(
                            f"denylist:{token.jti}",
                            "1",
                            ex=remaining_ttl,
                        )
                        session_count += 1
                    except Exception:
                        logger.warning(
                            "Failed to add JTI %s to Redis denylist",
                            token.jti,
                        )

        logger.info(
            "Admin %s revoked by %s, %d sessions invalidated",
            admin_user_id,
            revoked_by,
            session_count,
        )

        return session_count
