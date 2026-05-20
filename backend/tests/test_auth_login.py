import pytest

from tests.conftest import register_user, login_user


@pytest.mark.asyncio
async def test_login_success(client):
    await register_user(client, email="login@mayorista.com", nombre_negocio="Login Test Business")
    response = await login_user(client, email="login@mayorista.com")
    assert response.status_code == 200
    assert "access_token" in response.cookies


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
    await login_user(client, email="logout@mayorista.com")
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_me_endpoint(client):
    await register_user(client, email="me@mayorista.com", nombre_negocio="Me Test Business")
    await login_user(client, email="me@mayorista.com")
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@mayorista.com"
    assert data["nombre_negocio"] == "Me Test Business"
    assert data["prendas_count"] == 0


@pytest.mark.asyncio
async def test_me_without_auth(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in [401, 403]
