"""Pydantic schemas for two-factor authentication endpoints."""

from pydantic import BaseModel, Field


class TwoFactorSetupRequest(BaseModel):
    """Request to initiate 2FA setup."""

    method: str = Field(..., description="2FA method: 'totp' or 'sms'")
    phone_number: str | None = Field(
        None, description="Phone number in E.164 format (required for SMS)"
    )


class TotpSetupResponse(BaseModel):
    """Response from TOTP setup initiation."""

    totp_secret: str
    otpauth_uri: str
    backup_codes: list[str]


class SmsSetupResponse(BaseModel):
    """Response from SMS setup initiation."""

    phone_number: str
    otp_sent: bool


class TwoFactorConfirmRequest(BaseModel):
    """Request to confirm 2FA setup."""

    otp_code: str = Field(..., min_length=6, max_length=6)


class TwoFactorConfirmResponse(BaseModel):
    """Response from 2FA setup confirmation."""

    configured: bool
    method: str
    backup_codes_remaining: int


class TwoFactorChallengeRequest(BaseModel):
    """Request for TOTP or backup code challenge."""

    otp_code: str | None = Field(None, description="TOTP code (6 digits)")
    backup_code: str | None = Field(None, description="Backup recovery code (8 chars)")


class TwoFactorChallengeResponse(BaseModel):
    """Response from successful 2FA challenge."""

    challenge_consumed: bool


class SmsOtpSendRequest(BaseModel):
    """Request to send SMS OTP during challenge."""

    pass


class SmsOtpSendResponse(BaseModel):
    """Response from SMS OTP send."""

    otp_sent: bool
    phone_masked: str


class SmsOtpVerifyRequest(BaseModel):
    """Request to verify SMS OTP during challenge."""

    otp_code: str = Field(..., min_length=6, max_length=6)


class SmsOtpVerifyResponse(BaseModel):
    """Response from successful SMS OTP verification."""

    challenge_consumed: bool
