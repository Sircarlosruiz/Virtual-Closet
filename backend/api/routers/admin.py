"""Admin invitation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.tenant import (
    AcceptInvitationRequest,
    AdminInviteRequest,
    AdminInvitationResponse,
    AdminListResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.admin_invitation_repo import AdminInvitationRepo
from repositories.tenant_repo import TenantRepo
from services.admin_invitation_service import (
    AdminInvitationService,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    PendingInvitationExistsError,
)
from services.tenant_service import TenantInactiveError, TenantNotFoundError

router = APIRouter(prefix="/api/tenants/admins", tags=["tenant-admins"])


def _get_admin_invitation_service(
    db: AsyncSession = Depends(get_db),
) -> AdminInvitationService:
    invitation_repo = AdminInvitationRepo(db)
    tenant_repo = TenantRepo(db)
    return AdminInvitationService(invitation_repo, tenant_repo)


@router.post(
    "/invite",
    response_model=AdminInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_admin(
    body: AdminInviteRequest,
    mayorista: Mayorista = Depends(get_current_mayorista),
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """Invite a new admin to the tenant by email."""
    try:
        invitation = await admin_service.invite_admin(
            tenant_id=mayorista.tenant_id,
            email=body.email,
            created_by=mayorista.id,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TenantInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except PendingInvitationExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    # TODO: Send invitation email
    # from services.email_service import send_admin_invitation_email
    # await send_admin_invitation_email(body.email, invitation.token)

    return invitation


@router.get("", response_model=AdminListResponse)
async def list_admins(
    mayorista: Mayorista = Depends(get_current_mayorista),
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """List all admin invitations for the current tenant."""
    try:
        invitations = await admin_service.list_invitations(
            tenant_id=mayorista.tenant_id,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return AdminListResponse(invitations=invitations)


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_admin(
    admin_id: str,
    mayorista: Mayorista = Depends(get_current_mayorista),
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """Revoke an admin invitation or access.

    Note: This is a placeholder. Full implementation requires
    a user management system with admin roles.
    """
    # TODO: Implement full admin revocation with session invalidation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin revocation not yet implemented",
    )


@router.post(
    "/accept",
    response_model=AdminInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    body: AcceptInvitationRequest,
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """Accept an admin invitation and register a new user.

    Note: This is a placeholder. Full implementation requires
    user registration logic.
    """
    try:
        invitation = await admin_service.accept_invitation(
            token=body.token,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvitationExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvitationAlreadyAcceptedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    # TODO: Register new user with admin role
    # - Validate email matches invitation email
    # - Create user account with password
    # - Assign admin role within tenant

    return invitation
