"""Pydantic schemas for password reset endpoints."""

from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response from forgot password request (always identical)."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Request to complete password reset."""

    token: str = Field(..., min_length=64, max_length=64)
    new_password: str = Field(
        ...,
        min_length=8,
        description="Password must be at least 8 characters",
    )


class ResetPasswordResponse(BaseModel):
    """Response from successful password reset."""

    message: str
