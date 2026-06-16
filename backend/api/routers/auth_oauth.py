"""OAuth exchange endpoints.

Handles Google OAuth session exchange for challenge_token issuance
and account linking (ADR-024).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.oauth import (
    OAuthExchangeRequest,
    OAuthExchangeResponse,
    AccountLinkingRequest,
    AccountLinkingResponse,
)
from core.database import get_db
from repositories.mayorista_repo import MayoristaRepository
from repositories.oauth_link_repo import OAuthLinkRepository
from repositories.two_factor_config_repo import TwoFactorConfigRepository
from repositories.tenant_repo import TenantRepo
from services.oauth_exchange_service import (
    OAuthExchangeService,
    OAuthTokenInvalidError,
    AccountLinkingRequiredError,
    AccountLinkingRejectedError,
    OAuthExchangeError,
)
from services.auth_service import InvalidCredentialsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])


def _get_oauth_exchange_service(db: AsyncSession) -> OAuthExchangeService:
    """Factory for OAuthExchangeService."""
    return OAuthExchangeService(
        mayorista_repo=MayoristaRepository(db),
        oauth_link_repo=OAuthLinkRepository(db),
        two_factor_repo=TwoFactorConfigRepository(db),
        tenant_repo=TenantRepo(db),
    )


@router.post(
    "/exchange",
    response_model=OAuthExchangeResponse,
    responses={
        400: {"description": "Invalid or missing OAuth token"},
        409: {"description": "Account linking required"},
    },
)
async def oauth_exchange(
    exchange_data: OAuthExchangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange NextAuth Google session for a challenge_token.

    NextAuth verifies the Google identity server-side before calling this endpoint.
    The returned challenge_token requires 2FA before JWT issuance.

    If the Google email matches an existing email+password account,
    returns requires_account_linking=true (ADR-024).
    """
    service = _get_oauth_exchange_service(db)

    try:
        result = await service.exchange(
            provider=exchange_data.provider,
            provider_sub="google_sub",  # TODO: extract from nextauth_token
            provider_email="user@example.com",  # TODO: extract from nextauth_token
        )
        return OAuthExchangeResponse(
            challenge_token=result["challenge_token"],
            requires_2fa_setup=result.get("requires_2fa_setup", False),
            requires_2fa_challenge=result.get("requires_2fa_challenge", False),
            requires_business_name=result.get("requires_business_name", False),
        )
    except AccountLinkingRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ACCOUNT_LINKING_REQUIRED",
                "message": "An account exists with this email. Enter your password to link.",
                "email": e.email,
            },
        )
    except OAuthTokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_OAUTH_TOKEN",
                "message": "Google login failed, please try again or use email/password",
            },
        )
    except OAuthExchangeError as e:
        logger.exception("OAuth exchange failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "OAUTH_EXCHANGE_FAILED",
                "message": "Google login failed, please try again or use email/password",
            },
        )


@router.post(
    "/link",
    response_model=AccountLinkingResponse,
    responses={
        401: {"description": "Password incorrect"},
        404: {"description": "Account not found"},
    },
)
async def link_account(
    link_data: AccountLinkingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Link Google OAuth identity to an existing email+password account.

    Requires password confirmation (ADR-024) to prevent account takeover.
    """
    # Extract user_id from challenge_token (from initial exchange)
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    from core.security import decode_challenge_token

    payload = decode_challenge_token(challenge_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"},
        )

    mayorista_id = payload.get("sub")
    if not mayorista_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"},
        )

    service = _get_oauth_exchange_service(db)

    try:
        from uuid import UUID

        result = await service.link_account(
            mayorista_id=UUID(mayorista_id),
            password=link_data.password,
            provider=link_data.provider,
            provider_sub=link_data.provider_sub,
            provider_email=link_data.provider_email,
        )
        return AccountLinkingResponse(
            challenge_token=result["challenge_token"],
            requires_2fa_setup=result.get("requires_2fa_setup", False),
            requires_2fa_challenge=result.get("requires_2fa_challenge", False),
            linked=result.get("linked", False),
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_PASSWORD", "message": "Password incorrect"},
        )
    except OAuthExchangeError as e:
        logger.exception("Account linking failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "LINKING_FAILED", "message": str(e)},
        )
