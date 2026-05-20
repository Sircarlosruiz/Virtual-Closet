import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def registered_user(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "login@mayorista.com",
            "password": "password123",
            "nombre_negocio": "Login Test Business",
        },
    )


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "login@mayorista.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, registered_user):
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "login@mayorista.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@mayorista.com",
            "password": "password123",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, registered_user):
    await client.post(
        "/api/auth/login",
        json={
            "email": "login@mayorista.com",
            "password": "password123",
        },
    )
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "access_token" not in response.cookies


@pytest.mark.asyncio
async def test_me_endpoint(client, registered_user):
    await client.post(
        "/api/auth/login",
        json={
            "email": "login@mayorista.com",
            "password": "password123",
        },
    )
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "login@mayorista.com"
    assert data["nombre_negocio"] == "Login Test Business"
    assert data["prendas_count"] == 0


@pytest.mark.asyncio
async def test_me_without_auth(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in [401, 403]
