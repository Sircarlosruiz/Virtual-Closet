import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@mayorista.com",
            "password": "password123",
            "nombre_negocio": "Test Business",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@mayorista.com"
    assert data["nombre_negocio"] == "Test Business"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post(
        "/api/auth/register",
        json={
            "email": "dup@mayorista.com",
            "password": "password123",
            "nombre_negocio": "First Business",
        },
    )
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "dup@mayorista.com",
            "password": "password456",
            "nombre_negocio": "Second Business",
        },
    )
    assert response.status_code == 409
    assert "Este email ya está registrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "short@mayorista.com",
            "password": "123",
            "nombre_negocio": "Test Business",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "nombre_negocio": "Test Business",
        },
    )
    assert response.status_code == 422
