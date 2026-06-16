"""Two-factor authentication endpoints.

Handles TOTP setup/confirmation, 2FA challenge, and SMS OTP flows.
All endpoints require a valid challenge_token (except setup initiation
which creates one via login).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.two_factor import (
    TwoFactorChallengeRequest,
    TwoFactorChallengeResponse,
    TwoFactorConfirmRequest,
    TwoFactorConfirmResponse,
    TwoFactorSetupRequest,
    SmsOtpSendRequest,
    SmsOtpSendResponse,
    SmsOtpVerifyRequest,
    SmsOtpVerifyResponse,
    TotpSetupResponse,
    SmsSetupResponse,
)
from core.database import get_db
from core.security import decode_challenge_token
from repositories.backup_code_repo import BackupCodeRepository
from repositories.two_factor_config_repo import TwoFactorConfigRepository
from services.sms_otp_service import (
    SmsOtpService,
    SmsRateLimitExceededError,
    SmsDeliveryError,
)
from services.two_factor_setup_service import (
    TwoFactorSetupService,
    TwoFactorAlreadyConfiguredError,
    InvalidOtpCodeError,
    InvalidPhoneNumberError,
)
from services.two_factor_challenge_service import (
    TwoFactorChallengeService,
    TwoFactorNotConfiguredError,
    InvalidChallengeTokenError,
    MaxOtpAttemptsExceededError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/2fa", tags=["2fa"])


def _get_two_factor_setup_service(db: AsyncSession) -> TwoFactorSetupService:
    """Factory for TwoFactorSetupService."""
    return TwoFactorSetupService(
        two_factor_repo=TwoFactorConfigRepository(db),
        backup_code_repo=BackupCodeRepository(db),
        sms_otp_service=SmsOtpService(),
    )


def _get_two_factor_challenge_service(db: AsyncSession) -> TwoFactorChallengeService:
    """Factory for TwoFactorChallengeService."""
    return TwoFactorChallengeService(
        two_factor_repo=TwoFactorConfigRepository(db),
        backup_code_repo=BackupCodeRepository(db),
        sms_otp_service=SmsOtpService(),
    )


def _extract_user_id_from_challenge(challenge_token: str | None) -> UUID:
    """Extract and validate user_id from challenge_token.

    Raises HTTPException 401 if token is invalid or expired.
    """
    if not challenge_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"},
        )

    payload = decode_challenge_token(challenge_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"},
        )

    return UUID(user_id)


@router.post(
    "/setup",
    response_model=TotpSetupResponse | SmsSetupResponse,
    responses={
        401: {"description": "Invalid or expired challenge_token"},
        409: {"description": "2FA already configured"},
    },
)
async def setup_2fa(
    request: Request,
    setup_data: TwoFactorSetupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Initiate 2FA setup (TOTP or SMS).

    Requires a valid challenge_token. For TOTP, returns secret + QR URI + backup codes.
    For SMS, sends a confirmation OTP to the provided phone number.
    """
    # Extract challenge_token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    mayorista_id = _extract_user_id_from_challenge(challenge_token)

    service = _get_two_factor_setup_service(db)

    try:
        if setup_data.method == "totp":
            # Need email for otpauth URI — fetch from DB
            from repositories.mayorista_repo import MayoristaRepository

            mayorista_repo = MayoristaRepository(db)
            mayorista = await mayorista_repo.get_by_id(mayorista_id)
            if mayorista is None:
                raise HTTPException(status_code=404, detail="User not found")

            result = await service.initiate_totp_setup(mayorista_id, mayorista.email)
            return TotpSetupResponse(
                totp_secret=result["totp_secret"],
                otpauth_uri=result["otpauth_uri"],
                backup_codes=result["backup_codes"],
            )
        elif setup_data.method == "sms":
            if not setup_data.phone_number:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "MISSING_PHONE", "message": "phone_number is required for SMS"},
                )
            result = await service.initiate_sms_setup(mayorista_id, setup_data.phone_number)
            return SmsSetupResponse(
                phone_number=result["phone_number"],
                otp_sent=result["otp_sent"],
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_METHOD", "message": "method must be 'totp' or 'sms'"},
            )
    except TwoFactorAlreadyConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_CONFIGURED", "message": "Two-factor authentication is already set up"},
        )
    except InvalidPhoneNumberError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PHONE", "message": "Invalid phone number format"},
        )
    except SmsRateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "SMS_RATE_LIMITED",
                "message": f"Rate limit exceeded; try again in {e.retry_after} seconds",
                "retry_after": e.retry_after,
            },
        )
    except SmsDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "SMS_DELIVERY_FAILED", "message": "SMS could not be sent. Please use a backup code."},
        )


@router.post(
    "/setup/confirm",
    response_model=TwoFactorConfirmResponse,
    responses={
        401: {"description": "Invalid or expired challenge_token"},
        400: {"description": "Invalid OTP code"},
        409: {"description": "2FA already configured"},
    },
)
async def confirm_2fa_setup(
    request: Request,
    confirm_data: TwoFactorConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Confirm 2FA setup by submitting the TOTP or SMS OTP code."""
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    mayorista_id = _extract_user_id_from_challenge(challenge_token)

    service = _get_two_factor_setup_service(db)

    try:
        result = await service.confirm_totp_setup(mayorista_id, confirm_data.otp_code)
        return TwoFactorConfirmResponse(**result)
    except InvalidOtpCodeError:
        # Try SMS confirmation
        try:
            result = await service.confirm_sms_setup(mayorista_id, confirm_data.otp_code)
            return TwoFactorConfirmResponse(**result)
        except InvalidOtpCodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_OTP", "message": "Invalid code"},
            )
    except TwoFactorAlreadyConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_CONFIGURED", "message": "Two-factor authentication is already set up"},
        )


@router.post(
    "/challenge",
    response_model=TwoFactorChallengeResponse,
    responses={
        401: {"description": "Invalid or expired challenge_token"},
        400: {"description": "Invalid code"},
        429: {"description": "Max attempts exceeded"},
    },
)
async def challenge_2fa(
    request: Request,
    challenge_data: TwoFactorChallengeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit TOTP or backup code during 2FA challenge.

    On success, consumes the challenge_token and signals to the session
    service that JWT can be issued.
    """
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    mayorista_id = _extract_user_id_from_challenge(challenge_token)

    service = _get_two_factor_challenge_service(db)

    try:
        # Try backup code first if provided
        if challenge_data.backup_code:
            result = await service.validate_backup_code(mayorista_id, challenge_data.backup_code)
            # Consume challenge token
            payload = decode_challenge_token(challenge_token)
            await service.consume_challenge_token(payload["jti"] if "jti" in payload else challenge_token[:8])
            return TwoFactorChallengeResponse(challenge_consumed=True)

        # Try TOTP
        if challenge_data.otp_code:
            await service.validate_totp(mayorista_id, challenge_data.otp_code)
            # Consume challenge token
            payload = decode_challenge_token(challenge_token)
            await service.consume_challenge_token(payload["jti"] if "jti" in payload else challenge_token[:8])
            return TwoFactorChallengeResponse(challenge_consumed=True)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_CODE", "message": "Either otp_code or backup_code is required"},
        )
    except TwoFactorNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NOT_CONFIGURED", "message": "Two-factor authentication is not set up"},
        )
    except InvalidChallengeTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_OTP", "message": "Invalid code"},
        )
    except MaxOtpAttemptsExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "MAX_OTP_ATTEMPTS", "message": str(e)},
        )


@router.post(
    "/sms/send",
    response_model=SmsOtpSendResponse,
    responses={
        401: {"description": "Invalid or expired challenge_token"},
        409: {"description": "SMS 2FA not configured"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def send_sms_otp(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Send SMS OTP during 2FA challenge.

    Requires a valid challenge_token and SMS 2FA to be configured.
    """
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    mayorista_id = _extract_user_id_from_challenge(challenge_token)

    # Check 2FA config
    two_factor_repo = TwoFactorConfigRepository(db)
    config = await two_factor_repo.get_by_mayorista_id(mayorista_id)
    if config is None or not config.is_configured or config.method != "sms":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SMS_NOT_CONFIGURED", "message": "SMS 2FA is not configured"},
        )

    # Get phone number
    from core.security import decrypt_value

    phone_number = decrypt_value(config.phone_number_encrypted)

    sms_service = SmsOtpService()

    try:
        await sms_service.send_otp(mayorista_id, phone_number)
        from services.two_factor_setup_service import TwoFactorSetupService

        return SmsOtpSendResponse(
            otp_sent=True,
            phone_masked=TwoFactorSetupService._mask_phone(phone_number),
        )
    except SmsRateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "SMS_RATE_LIMITED",
                "message": f"Rate limit exceeded; try again in {e.retry_after} seconds",
                "retry_after": e.retry_after,
            },
        )
    except SmsDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "SMS_DELIVERY_FAILED", "message": "SMS could not be sent. Please use a backup code."},
        )


@router.post(
    "/sms/verify",
    response_model=SmsOtpVerifyResponse,
    responses={
        401: {"description": "Invalid or expired challenge_token"},
        400: {"description": "Invalid or expired OTP"},
        429: {"description": "Max attempts exceeded"},
    },
)
async def verify_sms_otp(
    request: Request,
    verify_data: SmsOtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify SMS OTP during 2FA challenge.

    On success, consumes the challenge_token and signals JWT issuance.
    """
    auth_header = request.headers.get("Authorization", "")
    challenge_token = None
    if auth_header.startswith("Bearer "):
        challenge_token = auth_header[7:]

    mayorista_id = _extract_user_id_from_challenge(challenge_token)

    service = _get_two_factor_challenge_service(db)

    try:
        await service.validate_sms_otp(mayorista_id, verify_data.otp_code)
        # Consume challenge token
        payload = decode_challenge_token(challenge_token)
        await service.consume_challenge_token(payload["jti"] if "jti" in payload else challenge_token[:8])
        return SmsOtpVerifyResponse(challenge_consumed=True)
    except TwoFactorNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NOT_CONFIGURED", "message": "SMS 2FA is not configured"},
        )
    except InvalidChallengeTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_OTP", "message": "Invalid code"},
        )
