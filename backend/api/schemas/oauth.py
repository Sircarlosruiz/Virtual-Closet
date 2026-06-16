"""Pydantic schemas for OAuth exchange endpoints."""

from pydantic import BaseModel, Field


class OAuthExchangeRequest(BaseModel):
    """Request to exchange NextAuth session for challenge_token."""

    nextauth_token: str = Field(..., description="NextAuth session token")
    provider: str = Field(default="google", description="OAuth provider")


class OAuthExchangeResponse(BaseModel):
    """Response from OAuth exchange."""

    challenge_token: str | None = None
    requires_2fa_setup: bool = False
    requires_2fa_challenge: bool = False
    requires_business_name: bool = False
    requires_account_linking: bool = False
    email: str | None = None


class AccountLinkingRequest(BaseModel):
    """Request to link Google OAuth to existing account."""

    password: str = Field(..., description="Existing account password")
    provider: str = Field(default="google", description="OAuth provider")
    provider_sub: str = Field(..., description="Google subject ID")
    provider_email: str = Field(..., description="Google email")


class AccountLinkingResponse(BaseModel):
    """Response from successful account linking."""

    challenge_token: str
    requires_2fa_setup: bool
    requires_2fa_challenge: bool
    linked: bool
