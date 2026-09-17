import pytest

from tests.conftest import register_user, request_login, login_user, verify_user_email


@pytest.mark.asyncio
async def test_login_success_returns_challenge_token(client):
    await register_user(client, email="login@mayorista.com", nombre_negocio="Login Test Business")
    await verify_user_email(client, email="login@mayorista.com")

    response = await request_login(client, email="login@mayorista.com")
    assert response.status_code == 200
    data = response.json()
    assert "challenge_token" in data
    assert data["requires_2fa_setup"] is True


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    await register_user(client, email="login@mayorista.com", nombre_negocio="Login Test Business")
    response = await request_login(client, email="login@mayorista.com", password="wrongpassword")
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await request_login(client, email="nonexistent@mayorista.com")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    await register_user(client, email="logout@mayorista.com", nombre_negocio="Logout Test Business")
    await login_user(client, email="logout@mayorista.com")
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "access_token" not in client.cookies
    assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_me_without_auth(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in [401, 403]
