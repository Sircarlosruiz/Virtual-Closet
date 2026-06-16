"""Pydantic schemas for session management endpoints."""

from pydantic import BaseModel


class RefreshResponse(BaseModel):
    """Response from successful token refresh."""

    token_type: str = "Bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    """Response from successful logout."""

    message: str


class LogoutAllResponse(BaseModel):
    """Response from successful logout from all devices."""

    message: str
    revoked_count: int
