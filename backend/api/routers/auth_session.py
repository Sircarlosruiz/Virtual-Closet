"""Session management endpoints.

Handles token refresh, single-device logout, and all-devices logout.
Implements fail-closed behavior on Redis outage (ADR-027).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.auth_session import (
    LogoutAllResponse,
    LogoutResponse,
    RefreshResponse,
)
from core.config import settings
from core.database import get_db
from core.dependencies import get_current_mayorista
from core.security import decode_rs256_access_token
from models.mayorista import Mayorista
from repositories.refresh_token_repo import RefreshTokenRepository
from services.redis_denylist_service import RedisDenylistService, RedisUnavailableError
from services.session_service import (
    SessionService,
    InvalidRefreshTokenError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_session_service(db: AsyncSession) -> SessionService:
    """Factory for SessionService."""
    return SessionService(
        refresh_token_repo=RefreshTokenRepository(db),
        denylist_service=RedisDenylistService(),
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    responses={
        401: {"description": "Invalid, expired, or revoked refresh token"},
        503: {"description": "Redis denylist unavailable"},
    },
)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token: issue new access + refresh tokens.

    The old refresh token is immediately revoked and added to the
    Redis denylist (ADR-028). Fails closed if Redis is unavailable (ADR-027).
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_REFRESH_TOKEN", "message": "Session expired, please log in again"},
        )

    service = _get_session_service(db)

    try:
        result = await service.refresh_session(refresh_token)

        # Set new cookies
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=False,  # Access token needs to be readable by frontend
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=result["expires_in"],
        )
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        return RefreshResponse(
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

    except InvalidRefreshTokenError as e:
        # Clear cookies on invalid token
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": str(e)},
        )
    except RedisUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Session service temporarily unavailable",
            },
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    """Single-device logout.

    Revokes the current refresh token and clears cookies.
    """
    service = _get_session_service(db)

    if refresh_token:
        await service.revoke_session(refresh_token)

    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return LogoutResponse(message="Logged out successfully")


@router.post(
    "/logout-all",
    response_model=LogoutAllResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def logout_all(
    response: Response,
    mayorista: Mayorista = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db),
):
    """All-devices logout.

    Revokes all active refresh tokens for the current user.
    """
    service = _get_session_service(db)

    revoked_count = await service.revoke_all_sessions(mayorista.id)

    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    return LogoutAllResponse(
        message="Logged out from all devices",
        revoked_count=revoked_count,
    )
