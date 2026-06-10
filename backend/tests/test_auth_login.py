import pytest

from tests.conftest import register_user, login_user


@pytest.mark.asyncio
async def test_login_success_returns_challenge_token(client):
    await register_user(client, email="login@mayorista.com", nombre_negocio="Login Test Business")
    # Verify email first
    from models.mayorista import Mayorista
    from models.email_verification_token import EmailVerificationToken
    from sqlalchemy import select
    from core.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    result = await db.execute(select(Mayorista).where(Mayorista.email == "login@mayorista.com"))
    user = result.scalar_one_or_none()
    if user:
        token_result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used.is_(False),
            )
        )
        token = token_result.scalar_one_or_none()
        if token:
            await client.get(f"/api/auth/verify-email?token={token.token}")
    await db_gen.aclose()

    response = await login_user(client, email="login@mayorista.com")
    assert response.status_code == 200
    data = response.json()
    assert "challenge_token" in data
    assert data["requires_2fa_setup"] is True


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    await register_user(client, email="login@mayorista.com", nombre_negocio="Login Test Business")
    response = await login_user(client, email="login@mayorista.com", password="wrongpassword")
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await login_user(client, email="nonexistent@mayorista.com")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    await register_user(client, email="logout@mayorista.com", nombre_negocio="Logout Test Business")
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_me_without_auth(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in [401, 403]
