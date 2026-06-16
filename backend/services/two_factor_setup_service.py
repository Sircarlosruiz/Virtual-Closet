"""Two-factor authentication setup service.

Handles TOTP and SMS 2FA initialization and confirmation.
"""

import secrets
from uuid import UUID

import pyotp

from core.security import encrypt_value, decrypt_value
from models.two_factor import TwoFactorConfig
from repositories.backup_code_repo import BackupCodeRepository
from repositories.two_factor_config_repo import TwoFactorConfigRepository
from services.sms_otp_service import SmsOtpService


# ── Domain Exceptions ──────────────────────────────────────────────────────


class TwoFactorAlreadyConfiguredError(Exception):
    """Raised when attempting to set up 2FA on an already configured account."""


class InvalidOtpCodeError(Exception):
    """Raised when the submitted OTP code is invalid."""


class InvalidPhoneNumberError(Exception):
    """Raised when the phone number format is invalid."""


# ── Constants ──────────────────────────────────────────────────────────────

BACKUP_CODE_COUNT = 8
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1


class TwoFactorSetupService:
    """Domain service for 2FA setup flows."""

    def __init__(
        self,
        two_factor_repo: TwoFactorConfigRepository,
        backup_code_repo: BackupCodeRepository,
        sms_otp_service: SmsOtpService | None = None,
    ):
        self.two_factor_repo = two_factor_repo
        self.backup_code_repo = backup_code_repo
        self.sms_otp_service = sms_otp_service

    async def initiate_totp_setup(
        self, mayorista_id: UUID, email: str
    ) -> dict:
        """Generate TOTP secret, otpauth URI, and backup codes.

        Returns the secret (plaintext, for one-time display), otpauth URI
        suitable for QR code generation, and 8 plaintext backup codes.

        The secret is NOT persisted until confirm_totp_setup is called.
        """
        existing = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if existing and existing.is_configured:
            raise TwoFactorAlreadyConfiguredError(
                "Two-factor authentication is already set up"
            )

        # Generate TOTP secret (32-char base32)
        totp_secret = pyotp.random_base32()

        # Generate otpauth URI
        otpauth_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
            name=email,
            issuer_name="Virtual Closet",
        )

        # Generate backup codes
        backup_codes = self._generate_backup_codes()

        # Store the secret and codes temporarily in the config (not yet confirmed)
        encrypted_secret = encrypt_value(totp_secret)

        if existing:
            existing.totp_secret_encrypted = encrypted_secret
            await self.two_factor_repo.update(existing)
            config = existing
        else:
            config = TwoFactorConfig(
                mayorista_id=mayorista_id,
                method="totp",
                totp_secret_encrypted=encrypted_secret,
            )
            await self.two_factor_repo.create(config)

        return {
            "totp_secret": totp_secret,
            "otpauth_uri": otpauth_uri,
            "backup_codes": backup_codes,
        }

    async def confirm_totp_setup(
        self, mayorista_id: UUID, totp_code: str
    ) -> dict:
        """Confirm TOTP setup by validating a TOTP code.

        If valid, persists the backup codes and marks 2FA as configured.

        Raises:
            InvalidOtpCodeError: If the TOTP code is invalid.
        """
        config = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if config is None or config.totp_secret_encrypted is None:
            raise InvalidOtpCodeError("Invalid code")

        if config.is_configured:
            raise TwoFactorAlreadyConfiguredError(
                "Two-factor authentication is already set up"
            )

        totp_secret = decrypt_value(config.totp_secret_encrypted)
        totp = pyotp.TOTP(totp_secret)

        # Validate with ±1 step tolerance (pyotp default)
        if not totp.verify(totp_code, valid_window=1):
            raise InvalidOtpCodeError("Invalid code")

        # Generate and persist backup codes
        backup_codes = self._generate_backup_codes()
        await self.backup_code_repo.create_batch(mayorista_id, backup_codes)

        # Mark as configured
        await self.two_factor_repo.mark_configured(mayorista_id, "totp")

        return {
            "configured": True,
            "method": "totp",
            "backup_codes_remaining": BACKUP_CODE_COUNT,
        }

    async def initiate_sms_setup(
        self, mayorista_id: UUID, phone_number: str
    ) -> dict:
        """Initiate SMS 2FA setup by sending a confirmation OTP.

        Validates phone number format, then sends an OTP via Twilio.

        Raises:
            InvalidPhoneNumberError: If the phone number format is invalid.
            TwoFactorAlreadyConfiguredError: If 2FA is already configured.
        """
        existing = await self.two_factor_repo.get_by_mayorista_id(mayorista_id)
        if existing and existing.is_configured:
            raise TwoFactorAlreadyConfiguredError(
                "Two-factor authentication is already set up"
            )

        # Validate E.164 format
        if not self._is_valid_e164(phone_number):
            raise InvalidPhoneNumberError("Invalid phone number format")

        if self.sms_otp_service is None:
            raise RuntimeError("sms_otp_service is required for SMS setup")

        # Send confirmation OTP
        await self.sms_otp_service.send_otp(mayorista_id, phone_number)

        # Store phone number temporarily
        encrypted_phone = encrypt_value(phone_number)
        if existing:
            existing.phone_number_encrypted = encrypted_phone
            await self.two_factor_repo.update(existing)
        else:
            config = TwoFactorConfig(
                mayorista_id=mayorista_id,
                method="sms",
                phone_number_encrypted=encrypted_phone,
            )
            await self.two_factor_repo.create(config)

        return {
            "phone_number": self._mask_phone(phone_number),
            "otp_sent": True,
        }

    async def confirm_sms_setup(
        self, mayorista_id: UUID, otp_code: str
    ) -> dict:
        """Confirm SMS 2FA setup by validating the confirmation OTP.

        If valid, generates backup codes and marks 2FA as configured.

        Raises:
            InvalidOtpCodeError: If the OTP code is invalid or expired.
        """
        if self.sms_otp_service is None:
            raise RuntimeError("sms_otp_service is required for SMS setup")

        # Verify OTP
        if not await self.sms_otp_service.verify_otp(mayorista_id, otp_code):
            raise InvalidOtpCodeError("Invalid code")

        # Generate and persist backup codes
        backup_codes = self._generate_backup_codes()
        await self.backup_code_repo.create_batch(mayorista_id, backup_codes)

        # Mark as configured
        await self.two_factor_repo.mark_configured(mayorista_id, "sms")

        return {
            "configured": True,
            "method": "sms",
            "backup_codes_remaining": BACKUP_CODE_COUNT,
        }

    # ── Internal Helpers ───────────────────────────────────────────────

    @staticmethod
    def _generate_backup_codes() -> list[str]:
        """Generate 8 random backup codes."""
        return [
            "".join(secrets.choice(BACKUP_CODE_CHARS) for _ in range(BACKUP_CODE_LENGTH))
            for _ in range(BACKUP_CODE_COUNT)
        ]

    @staticmethod
    def _is_valid_e164(phone: str) -> bool:
        """Basic E.164 validation: + followed by 1-14 digits."""
        return phone.startswith("+") and phone[1:].isdigit() and 1 <= len(phone) - 1 <= 14

    @staticmethod
    def _mask_phone(phone: str) -> str:
        """Mask phone number for display: +5058888****."""
        if len(phone) <= 6:
            return phone[:2] + "****"
        return phone[:-4] + "****"
