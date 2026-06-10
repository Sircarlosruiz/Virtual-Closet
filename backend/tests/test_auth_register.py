import pytest

from tests.conftest import register_user


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@mayorista.com",
            "password": "Password1",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@mayorista.com"
    assert data["business_name"] == "Test Business"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await register_user(client, email="dup@mayorista.com")
    response = await register_user(client, email="dup@mayorista.com", password="Password456", nombre_negocio="Second Business")
    assert response.status_code == 409
    assert "Este email ya está registrado" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(client):
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
async def test_register_invalid_email(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "Password1",
            "business_name": "Test Business",
        },
    )
    assert response.status_code == 422
