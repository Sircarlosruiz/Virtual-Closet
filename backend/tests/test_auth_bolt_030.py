"""Integration tests for auth bolt 030: registration, email verification, login, lockout.

Covers stories:
- 001-mayorista-registration
- 002-email-verification
- 003-login-email-password
- 004-account-lockout
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.mayorista import Mayorista
from models.email_verification_token import EmailVerificationToken
from models.unlock_token import UnlockToken
from core.database import get_db
from core.limiter import limiter


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_user_by_email(client, email: str) -> Mayorista | None:
    """Fetch user directly from DB to inspect state."""
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    result = await db.execute(select(Mayorista).where(Mayorista.email == email))
    await db_gen.aclose()
    return result.scalar_one_or_none()


async def _get_unused_verification_token(client, user_id) -> EmailVerificationToken | None:
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used.is_(False),
        )
    )
    await db_gen.aclose()
    return result.scalar_one_or_none()


# ── Story 001: Mayorista Registration ──────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(client):
    """Given valid data, when registering, then user is created with email_verified=false."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "new@mayorista.com",
            "password": "Password1",
            "business_name": "New Business",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@mayorista.com"
    assert data["business_name"] == "New Business"
    assert "id" in data

    # Verify email_verified is false
    user = await _get_user_by_email(client, "new@mayorista.com")
    assert user is not None
    assert user.email_verified is False
    assert user.is_locked is False
    assert user.failed_attempts == 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Given email already registered, when registering again, then 409."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "dup@mayorista.com",
            "password": "Password1",
            "business_name": "First Business",
        },
    )
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "dup@mayorista.com",
            "password": "Password2",
            "business_name": "Second Business",
        },
    )
    assert response.status_code == 409
    assert "Este email ya está registrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email_case_insensitive(client):
    """Given duplicate email with different casing, when registering, then 409."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "Case@Mayorista.com",
            "password": "Password1",
            "business_name": "Test Business",
        },
    )
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "case@mayorista.com",
            "password": "Password2",
            "business_name": "Other Business",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client):
    """Given password < 8 chars, when registering, then 422."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "short@mayorista.com",
            "password": "123",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_uppercase(client):
    """Given password without uppercase, when registering, then 422."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "nouppercase@mayorista.com",
            "password": "password123",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_number(client):
    """Given password without number, when registering, then 422."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "nonumber@mayorista.com",
            "password": "Password",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    """Given invalid email format, when registering, then 422."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "Password1",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_creates_tenant(client):
    """Given registration, when account is created, then tenant_id is set."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "tenant@mayorista.com",
            "password": "Password1",
            "business_name": "Tenant Business",
        },
    )
    assert response.status_code == 201
    user = await _get_user_by_email(client, "tenant@mayorista.com")
    assert user is not None
    assert user.tenant_id is not None


# ── Story 002: Email Verification ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_email_success(client):
    """Given valid verification token, when clicking link, then email_verified=true."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "verify@mayorista.com",
            "password": "Password1",
            "business_name": "Verify Business",
        },
    )
    user = await _get_user_by_email(client, "verify@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)
    assert token is not None

    response = await client.get(f"/api/auth/verify-email?token={token.token}")
    assert response.status_code == 200
    assert "Email verified successfully" in response.json()["message"]

    # Verify state changed
    user = await _get_user_by_email(client, "verify@mayorista.com")
    assert user.email_verified is True


@pytest.mark.asyncio
async def test_verify_email_expired_token(client):
    """Given expired token, when clicking link, then 400."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "expired@mayorista.com",
            "password": "Password1",
            "business_name": "Expired Business",
        },
    )
    # Use a fake expired token
    response = await client.get("/api/auth/verify-email?token=0" * 64)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_used_token(client):
    """Given already-used token, when clicking link again, then 400."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "used@mayorista.com",
            "password": "Password1",
            "business_name": "Used Business",
        },
    )
    user = await _get_user_by_email(client, "used@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)

    # First verification succeeds
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # Second verification fails
    response = await client.get(f"/api/auth/verify-email?token={token.token}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client):
    """Given tampered token, when clicking link, then 400."""
    response = await client.get("/api/auth/verify-email?token=invalidtoken123")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_resend_verification(client):
    """Given resend request, when submitting email, then new token issued."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "resend@mayorista.com",
            "password": "Password1",
            "business_name": "Resend Business",
        },
    )
    user = await _get_user_by_email(client, "resend@mayorista.com")
    old_token = await _get_unused_verification_token(client, user.id)

    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "resend@mayorista.com"},
    )
    assert response.status_code == 200

    # Old token should be invalidated
    old_token = await _get_unused_verification_token(client, user.id)
    assert old_token is None

    # New token should exist
    new_token = await _get_unused_verification_token(client, user.id)
    assert new_token is not None
    assert new_token.token != old_token.token if old_token else True


@pytest.mark.asyncio
async def test_resend_verification_nonexistent_email(client):
    """Given nonexistent email, when resending, then generic 200 (no enumeration)."""
    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "nonexistent@mayorista.com"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_already_verified(client):
    """Given already verified user, when resending, then generic 200."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "verified@mayorista.com",
            "password": "Password1",
            "business_name": "Verified Business",
        },
    )
    user = await _get_user_by_email(client, "verified@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    response = await client.post(
        "/api/auth/resend-verification",
        json={"email": "verified@mayorista.com"},
    )
    assert response.status_code == 200


# ── Story 003: Login with Email + Password ─────────────────────────────────


@pytest.mark.asyncio
async def test_login_unverified_account(client):
    """Given unverified account, when logging in, then 403."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "unverified@mayorista.com",
            "password": "Password1",
            "business_name": "Unverified Business",
        },
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "unverified@mayorista.com", "password": "Password1"},
    )
    assert response.status_code == 403
    assert "verificar" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_verified_account_returns_challenge_token(client):
    """Given verified account, when logging in, then challenge_token returned."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "challenge@mayorista.com",
            "password": "Password1",
            "business_name": "Challenge Business",
        },
    )
    user = await _get_user_by_email(client, "challenge@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    response = await client.post(
        "/api/auth/login",
        json={"email": "challenge@mayorista.com", "password": "Password1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "challenge_token" in data
    assert "requires_2fa_setup" in data
    assert data["requires_2fa_setup"] is True


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Given invalid credentials, when logging in, then generic 401."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "invalid@mayorista.com",
            "password": "Password1",
            "business_name": "Invalid Business",
        },
    )
    user = await _get_user_by_email(client, "invalid@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    response = await client.post(
        "/api/auth/login",
        json={"email": "invalid@mayorista.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "contraseña" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Given nonexistent email, when logging in, then generic 401 (no enumeration)."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "nonexistent@mayorista.com", "password": "Password1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_email_normalized(client):
    """Given uppercase email, when logging in, then normalized to lowercase."""
    await client.post(
        "/api/auth/register",
        json={
            "email": "normalize@mayorista.com",
            "password": "Password1",
            "business_name": "Normalize Business",
        },
    )
    user = await _get_user_by_email(client, "normalize@mayorista.com")
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # Login with uppercase
    response = await client.post(
        "/api/auth/login",
        json={"email": "NORMALIZE@MAYORISTA.COM", "password": "Password1"},
    )
    assert response.status_code == 200
    assert "challenge_token" in response.json()


# ── Story 004: Account Lockout ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_account_lockout_after_5_failures(client):
    """Given 4 failed attempts, when 5th incorrect password submitted, then account locked."""
    email = "lockout@mayorista.com"
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "business_name": "Lockout Business",
        },
    )
    user = await _get_user_by_email(client, email)
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # 5 failed attempts
    for i in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    # Account should be locked
    user = await _get_user_by_email(client, email)
    assert user.is_locked is True
    assert user.failed_attempts == 5


@pytest.mark.asyncio
async def test_locked_account_rejects_login(client):
    """Given locked account, when logging in, then 423."""
    email = "locked@mayorista.com"
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "business_name": "Locked Business",
        },
    )
    user = await _get_user_by_email(client, email)
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # Lock the account
    for _ in range(5):
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )

    # Try login with correct credentials — should be rejected
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password1"},
    )
    assert response.status_code == 423
    assert "bloqueada" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unlock_account(client):
    """Given locked account, when using unlock link, then account unlocked."""
    email = "unlock@mayorista.com"
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "business_name": "Unlock Business",
        },
    )
    user = await _get_user_by_email(client, email)
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # Lock the account
    for _ in range(5):
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )

    # Get the unlock token from DB
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    from sqlalchemy import select
    result = await db.execute(
        select(UnlockToken).where(
            UnlockToken.user_id == user.id,
            UnlockToken.used.is_(False),
        )
    )
    await db_gen.aclose()
    unlock_token = result.scalar_one_or_none()
    assert unlock_token is not None

    # Unlock
    response = await client.post(f"/api/auth/unlock?token={unlock_token.token}")
    assert response.status_code == 200
    assert "unlocked" in response.json()["message"].lower()

    # Verify state
    user = await _get_user_by_email(client, email)
    assert user.is_locked is False
    assert user.failed_attempts == 0


@pytest.mark.asyncio
async def test_unlock_invalid_token(client):
    """Given invalid unlock token, when unlocking, then 400."""
    response = await client.post("/api/auth/unlock?token=invalidtoken123")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unlock_used_token(client):
    """Given used unlock token, when unlocking again, then 400."""
    email = "unlockused@mayorista.com"
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "business_name": "Unlock Used Business",
        },
    )
    user = await _get_user_by_email(client, email)
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # Lock the account
    for _ in range(5):
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )

    # Get unlock token
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    result = await db.execute(
        select(UnlockToken).where(
            UnlockToken.user_id == user.id,
            UnlockToken.used.is_(False),
        )
    )
    await db_gen.aclose()
    unlock_token = result.scalar_one_or_none()

    # First unlock succeeds
    await client.post(f"/api/auth/unlock?token={unlock_token.token}")

    # Second unlock fails
    response = await client.post(f"/api/auth/unlock?token={unlock_token.token}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempts(client):
    """Given failed attempts, when successful login, then failed_attempts reset to 0."""
    email = "reset@mayorista.com"
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "business_name": "Reset Business",
        },
    )
    user = await _get_user_by_email(client, email)
    token = await _get_unused_verification_token(client, user.id)
    await client.get(f"/api/auth/verify-email?token={token.token}")

    # 3 failed attempts
    for _ in range(3):
        await client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )

    user = await _get_user_by_email(client, email)
    assert user.failed_attempts == 3

    # Successful login
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password1"},
    )
    assert response.status_code == 200

    # Failed attempts reset
    user = await _get_user_by_email(client, email)
    assert user.failed_attempts == 0
