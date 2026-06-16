"""Password reset endpoints.

Handles forgot-password request and reset-password completion.
Implements no-enforcement pattern (ADR-029).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.auth_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from core.database import get_db
from core.limiter import limiter
from repositories.mayorista_repo import MayoristaRepository
from repositories.password_reset_token_repo import PasswordResetTokenRepository
from repositories.refresh_token_repo import RefreshTokenRepository
from services.password_reset_service import (
    PasswordResetService,
    InvalidResetTokenError,
    ExpiredResetTokenError,
    UsedResetTokenError,
)
from services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_password_reset_service(db: AsyncSession) -> PasswordResetService:
    """Factory for PasswordResetService."""
    refresh_token_repo = RefreshTokenRepository(db)
    session_service = SessionService(
        refresh_token_repo=refresh_token_repo,
    )
    return PasswordResetService(
        mayorista_repo=MayoristaRepository(db),
        reset_token_repo=PasswordResetTokenRepository(db),
        session_service=session_service,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("3/hour")
async def forgot_password(
    request,
    reset_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link.

    Returns identical response whether email exists or not (no enumeration).
    Rate limited to 3 requests per hour.
    """
    service = _get_password_reset_service(db)
    await service.request_reset(reset_data.email)

    # Always return the same response
    return ForgotPasswordResponse(
        message="If the email exists, a reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    responses={
        400: {"description": "Invalid, expired, or used token"},
        422: {"description": "Password validation error"},
    },
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Complete a password reset using the token from the email link.

    On success, updates password and revokes all active sessions.
    """
    service = _get_password_reset_service(db)

    try:
        await service.complete_reset(reset_data.token, reset_data.new_password)
    except InvalidResetTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESET_TOKEN", "message": "Invalid reset token"},
        )
    except ExpiredResetTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EXPIRED_RESET_TOKEN", "message": str(e)},
        )
    except UsedResetTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "USED_RESET_TOKEN", "message": str(e)},
        )

    return ResetPasswordResponse(message="Password reset successfully")
