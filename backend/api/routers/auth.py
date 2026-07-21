"""Authentication endpoints.

Handles mayorista registration, email verification, login (challenge_token),
account lockout, and unlock.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    UnlockResponse,
    VerifyEmailResponse,
)
from core.config import settings
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.limiter import limiter
from core.security import create_access_token
from models.mayorista import Mayorista
from repositories.email_verification_token_repo import EmailVerificationTokenRepository
from repositories.mayorista_repo import MayoristaRepository
from repositories.tenant_repo import TenantRepo
from repositories.two_factor_config_repo import TwoFactorConfigRepository
from repositories.unlock_token_repo import UnlockTokenRepository
from services.auth_service import (
    AccountLockedError,
    AuthService,
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from services.email_service import send_welcome_email, send_verification_email, send_unlock_email

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_auth_service(db: AsyncSession) -> AuthService:
    """Factory for AuthService with all required repositories."""
    return AuthService(
        mayorista_repo=MayoristaRepository(db),
        email_token_repo=EmailVerificationTokenRepository(db),
        unlock_token_repo=UnlockTokenRepository(db),
        tenant_repo=TenantRepo(db),
        two_factor_repo=TwoFactorConfigRepository(db),
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Este email ya está registrado"},
        422: {"description": "Validation error"},
    },
)
@limiter.limit("5/15minutes")
async def register(
    request: Request,
    register_data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new mayorista with email verification."""
    auth_service = _get_auth_service(db)

    try:
        mayorista, verification_token = await auth_service.register(
            email=register_data.email,
            password=register_data.password,
            business_name=register_data.business_name,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email ya está registrado",
        )

    # Send verification email (fire-and-forget)
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token.token}"
    )
    try:
        await send_verification_email(mayorista.email, mayorista.nombre_negocio, verification_url)
    except Exception:
        logger.exception("Failed to send verification email")

    return RegisterResponse(
        id=mayorista.id,
        email=mayorista.email,
        business_name=mayorista.nombre_negocio,
    )


@router.get(
    "/verify-email",
    response_model=VerifyEmailResponse,
    responses={
        400: {"description": "Invalid, expired, or used token"},
    },
)
async def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: AsyncSession = Depends(get_db),
):
    """Verify email address using the token from the verification link."""
    auth_service = _get_auth_service(db)

    try:
        await auth_service.verify_email(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return VerifyEmailResponse(message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("3/1hour")
async def resend_verification(
    request: Request,
    resend_data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend verification email. Returns 200 even if email not found (no enumeration)."""
    auth_service = _get_auth_service(db)

    try:
        verification_token = await auth_service.resend_verification(resend_data.email)
    except Exception:
        logger.exception("Failed to resend verification email")
        # Return generic success to prevent enumeration
        return ResendVerificationResponse(message="If the email exists, a verification link has been sent")

    if verification_token is None:
        # User not found or already verified — return generic success
        return ResendVerificationResponse(message="If the email exists, a verification link has been sent")

    # Send verification email
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token.token}"
    )
    try:
        mayorista = await auth_service.mayorista_repo.get_by_email(resend_data.email.lower())
        if mayorista:
            await send_verification_email(mayorista.email, mayorista.nombre_negocio, verification_url)
    except Exception:
        logger.exception("Failed to send verification email")

    return ResendVerificationResponse(message="If the email exists, a verification link has been sent")


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"description": "Email o contraseña incorrectos"},
        403: {"description": "Email not verified"},
        423: {"description": "Account locked"},
        429: {"description": "Demasiados intentos"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password. Returns challenge_token (not full JWT)."""
    auth_service = _get_auth_service(db)

    try:
        result = await auth_service.login(
            email=login_data.email,
            password=login_data.password,
        )
    except InvalidCredentialsError:
        # Record failed attempt (atomic increment)
        try:
            failed_attempts, is_locked = await auth_service.record_failed_login(login_data.email)
            if is_locked:
                # Create unlock token and send lockout email
                mayorista = await auth_service.mayorista_repo.get_by_email(login_data.email.lower())
                if mayorista:
                    unlock_token = await auth_service.create_unlock_token(mayorista.id)
                    unlock_url = f"{settings.FRONTEND_URL}/unlock?token={unlock_token.token}"
                    try:
                        await send_unlock_email(login_data.email.lower(), unlock_url)
                    except Exception:
                        logger.exception("Failed to send lockout email")
        except Exception:
            logger.exception("Failed to record failed login attempt")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    except EmailNotVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu email antes de iniciar sesión.",
        )
    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada. Revisa tu email para instrucciones de desbloqueo.",
        )

    return LoginResponse(
        challenge_token=result["challenge_token"],
        requires_2fa_setup=result["requires_2fa_setup"],
        requires_2fa=result["requires_2fa"],
    )


@router.post(
    "/unlock",
    response_model=UnlockResponse,
    responses={
        400: {"description": "Invalid, expired, or used token"},
    },
)
async def unlock(
    token: str = Query(..., description="Unlock token"),
    db: AsyncSession = Depends(get_db),
):
    """Unlock a locked account using the token from the lockout email."""
    auth_service = _get_auth_service(db)

    try:
        await auth_service.unlock_account(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UnlockResponse(message="Account unlocked successfully")


@router.get("/me", response_model=MeResponse)
async def me(
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    from repositories.prenda_repo import PrendaRepository

    repo = PrendaRepository(db)
    count = await repo.count_by_mayorista(mayorista.id)
    return MeResponse(
        id=mayorista.id,
        email=mayorista.email,
        nombre_negocio=mayorista.nombre_negocio,
        plan=mayorista.plan,
        trial_activo=mayorista.trial_activo,
        trial_expira_en=mayorista.trial_expira_en,
        prendas_count=count,
    )
