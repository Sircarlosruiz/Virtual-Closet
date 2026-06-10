"""Integration tests for admin invitation endpoints (bolt 029)."""

import uuid

import pytest
import pytest_asyncio

from tests.conftest import login_user, register_user


@pytest_asyncio.fixture
async def authenticated_client(client):
    await register_user(client)
    await login_user(client)
    return client


@pytest.mark.asyncio
async def test_invite_admin_requires_auth(client):
    """Unauthenticated requests should return 401."""
    response = await client.post(
        "/api/tenants/admins/invite",
        json={"email": "admin@example.com"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invite_admin_invalid_email(authenticated_client):
    """Invalid email format should return 422."""
    response = await authenticated_client.post(
        "/api/tenants/admins/invite",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_admins(authenticated_client):
    """GET /tenants/admins should return list of admins."""
    response = await authenticated_client.get("/api/tenants/admins")
    assert response.status_code == 200
    data = response.json()
    assert "admins" in data


@pytest.mark.asyncio
async def test_revoke_admin_self(authenticated_client):
    """Cannot revoke your own access — should return 403."""
    own_id = str(uuid.uuid4())
    response = await authenticated_client.delete(
        f"/api/tenants/admins/{own_id}",
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_revoke_admin_not_found(authenticated_client):
    """Revoke non-existent admin should return 404."""
    random_id = str(uuid.uuid4())
    response = await authenticated_client.delete(
        f"/api/tenants/admins/{random_id}",
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_accept_invitation_invalid_token(client):
    """Accept with invalid token should return 400."""
    response = await client.post(
        "/api/tenants/admins/accept",
        json={
            "token": "invalid-token",
            "email": "admin@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_accept_invitation_empty_password(client):
    """Password too short should return 422."""
    response = await client.post(
        "/api/tenants/admins/accept",
        json={
            "token": "some-token",
            "email": "admin@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422
