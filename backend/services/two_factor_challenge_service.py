"""Two-factor authentication challenge service.

Handles TOTP, SMS OTP, and backup code validation during login.
Consumes challenge tokens on successful 2FA (ADR-025).
"""

import logging
from uuid import UUID

import pyotp

from core.redis_client import get_redis
from core.security import decrypt_value
from repositories.backup_code_repo import BackupCodeRepository
from repositories.two_factor_config_repo import TwoFactorConfigRepository
from services.sms_otp_service import SmsOtpService

logger = logging.getLogger(__name__)

# ── Domain Exceptions ──────────────────────────────────────────────────────


class InvalidChallengeTokenError(Exception):
    """Raised when the challenge token is invalid, expired, or already consumed."""


class TwoFactorNotConfiguredError(Exception):
    """Raised when attempting 2FA challenge on an account without 2FA setup."""


class MaxOtpAttemptsExceededError(Exception):
    """Raised when max TOTP attempts are exceeded."""


# ── Constants ──────────────────────────────────────────────────────────────

MAX_TOTP_ATTEMPTS = 5


class TwoFactorChallengeService:
    """Domain service for 2FA challenge validation."""

    def __init__(
        self,
        two_factor_repo: TwoFactorConfigRepository,
        backup_code_repo: BackupCodeRepository,
        sms_otp_service: SmsOtpService | None = None,
    ):
        self.two_factor_repo = two_factor_repo
        self.backup_code_repo = backup_code_repo
        self.sms_otp_service = sms_otp_service
        self._totp_attempt_counts: dict[UUID, int] = {}

    async def validate_totp(
        self, mayorista_id: UUID, totp_code: str
    ) -> bool:
        """Validate a TOTP code during 2FA challenge.

        Uses replay protection via Redis (ADR-023) to prevent the same
        code from being used twice within the validity window.

        Raises:
            TwoFactorNotConfiguredError: If 2FA is not configured.
            InvalidChallengeTokenError: If the TOTP code is invalid.
            MaxOtpAttemptsExceededError: If max attempts exceeded.
        """
        config = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if config is None or not config.is_configured:
            raise TwoFactorNotConfiguredError(
                "Two-factor authentication is not set up"
            )

        if config.method != "totp" or config.totp_secret_encrypted is None:
            raise InvalidChallengeTokenError("Invalid code")

        totp_secret = decrypt_value(config.totp_secret_encrypted)
        totp = pyotp.TOTP(totp_secret)

        # Check replay protection via Redis
        redis = await get_redis()
        if redis:
            replay_key = f"totp:used:{mayorista_id}:{totp_code}"
            is_replay = await redis.exists(replay_key)
            if is_replay:
                raise InvalidChallengeTokenError("Invalid code")

        # Validate with ±1 step tolerance
        if not totp.verify(totp_code, valid_window=1):
            # Track attempts
            attempts = self._totp_attempt_counts.get(mayorista_id, 0) + 1
            self._totp_attempt_counts[mayorista_id] = attempts
            if attempts >= MAX_TOTP_ATTEMPTS:
                raise MaxOtpAttemptsExceededError(
                    "Too many attempts. Please log in again."
                )
            raise InvalidChallengeTokenError("Invalid code")

        # Mark code as used (replay protection)
        if redis:
            replay_key = f"totp:used:{mayorista_id}:{totp_code}"
            await redis.setex(replay_key, 90, "1")  # 90s covers ±1 step window

        # Clear attempt counter on success
        self._totp_attempt_counts.pop(mayorista_id, None)
        return True

    async def validate_backup_code(
        self, mayorista_id: UUID, code_plaintext: str
    ) -> dict:
        """Validate a backup recovery code during 2FA challenge.

        Consumes the code (single-use) on success.

        Raises:
            TwoFactorNotConfiguredError: If 2FA is not configured.
            InvalidChallengeTokenError: If the backup code is invalid.
        """
        config = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if config is None or not config.is_configured:
            raise TwoFactorNotConfiguredError(
                "Two-factor authentication is not set up"
            )

        consumed = await self.backup_code_repo.verify_and_consume(
            mayorista_id, code_plaintext
        )
        if not consumed:
            raise InvalidChallengeTokenError("Invalid code")

        # Decrement backup codes remaining
        remaining = await self.two_factor_repo.decrement_backup_codes(mayorista_id)

        return {
            "valid": True,
            "remaining_codes": remaining or 0,
            "requires_regeneration": (remaining or 0) == 0,
        }

    async def validate_sms_otp(
        self, mayorista_id: UUID, otp_code: str
    ) -> bool:
        """Validate an SMS OTP during 2FA challenge.

        Delegates to SmsOtpService for Redis-based verification.

        Raises:
            TwoFactorNotConfiguredError: If 2FA is not configured.
            InvalidChallengeTokenError: If the OTP is invalid.
        """
        config = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if config is None or not config.is_configured:
            raise TwoFactorNotConfiguredError(
                "Two-factor authentication is not set up"
            )

        if config.method != "sms":
            raise InvalidChallengeTokenError("Invalid code")

        if self.sms_otp_service is None:
            raise RuntimeError("sms_otp_service is required for SMS challenge")

        valid = await self.sms_otp_service.verify_otp(mayorista_id, otp_code)
        if not valid:
            raise InvalidChallengeTokenError("Invalid code")

        return True

    async def consume_challenge_token(self, jti: str) -> bool:
        """Mark a challenge token as consumed via Redis (ADR-025).

        Returns True if successfully consumed, False if already consumed.
        """
        redis = await get_redis()

        if redis is None:
            logger.warning("Redis unavailable — challenge token single-use enforcement skipped")
            return True

        key = f"challenge:consumed:{jti}"
        # SETNX: only set if key does not exist
        result = await redis.set(key, "1", nx=True, ex=300)
        return result is not None and result
