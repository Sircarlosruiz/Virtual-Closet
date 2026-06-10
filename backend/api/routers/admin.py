"""Admin invitation API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.tenant import (
    AcceptInvitationRequest,
    AdminInviteRequest,
    AdminInvitationResponse,
    AdminListResponse,
    AdminResponse,
)
from core.database import get_db
from core.dependencies import get_current_mayorista
from models.mayorista import Mayorista
from repositories.admin_invitation_repo import AdminInvitationRepo
from repositories.mayorista_repo import MayoristaRepository
from repositories.tenant_repo import TenantRepo
from services.admin_invitation_service import (
    AdminInvitationService,
    AdminNotFoundError,
    AdminRevocationError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    MaxInvitationsReachedError,
    PendingInvitationExistsError,
)
from services.auth_service import AuthService, EmailAlreadyExistsError
from services.tenant_service import TenantInactiveError, TenantNotFoundError

router = APIRouter(prefix="/api/tenants/admins", tags=["tenant-admins"])


def _get_admin_invitation_service(
    db: AsyncSession = Depends(get_db),
) -> AdminInvitationService:
    invitation_repo = AdminInvitationRepo(db)
    tenant_repo = TenantRepo(db)
    mayorista_repo = MayoristaRepository(db)
    return AdminInvitationService(invitation_repo, tenant_repo, mayorista_repo)


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
            tenant_name=mayorista.nombre_negocio,
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
    except MaxInvitationsReachedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc

    return invitation


@router.get("", response_model=AdminListResponse)
async def list_admins(
    mayorista: Mayorista = Depends(get_current_mayorista),
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """List all active admins in the current tenant."""
    try:
        admins = await admin_service.list_admins(
            tenant_id=mayorista.tenant_id,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return AdminListResponse(
        admins=[
            AdminResponse(
                id=admin.id,
                email=admin.email,
                role=admin.role,
                created_at=admin.created_at,
            )
            for admin in admins
        ]
    )


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_admin(
    admin_id: str,
    mayorista: Mayorista = Depends(get_current_mayorista),
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
):
    """Revoke an admin's access and invalidate their sessions."""
    try:
        await admin_service.revoke_admin(
            tenant_id=mayorista.tenant_id,
            admin_user_id=uuid.UUID(admin_id),
            revoked_by=mayorista.id,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AdminNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AdminRevocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.post(
    "/accept",
    response_model=AdminInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation(
    body: AcceptInvitationRequest,
    admin_service: AdminInvitationService = Depends(_get_admin_invitation_service),
    db: AsyncSession = Depends(get_db),
):
    """Accept an admin invitation and register a new user."""
    try:
        invitation = await admin_service.get_invitation(token=body.token)

        if invitation.email != body.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match invitation",
            )

        mayorista_repo = MayoristaRepository(db)
        existing = await mayorista_repo.get_by_email(body.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered on the platform",
            )

        auth_service = AuthService(mayorista_repo)
        new_admin = await auth_service.register(
            email=body.email,
            password=body.password,
            nombre_negocio="",
        )

        await mayorista_repo.update_role(new_admin.id, "admin")

        from models.tenant import Tenant

        tenant_result = await db.execute(
            Tenant.__table__.select().where(Tenant.id == invitation.tenant_id)
        )
        tenant_row = tenant_result.first()
        if tenant_row:
            new_admin.tenant_id = invitation.tenant_id
            await db.commit()
            await db.refresh(new_admin)

        await admin_service.accept_invitation(token=body.token)

        return invitation

    except InvitationExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvitationAlreadyAcceptedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except TenantNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
