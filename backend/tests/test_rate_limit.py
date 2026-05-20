import pytest

from tests.conftest import register_user


@pytest.mark.asyncio
async def test_login_rate_limit(client):
    await register_user(client, email="ratelimit@mayorista.com", nombre_negocio="Rate Limit Test")

    for _ in range(10):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "ratelimit@mayorista.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/api/auth/login",
        json={"email": "ratelimit@mayorista.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 429
    assert "Demasiados intentos" in resp.json()["detail"]
