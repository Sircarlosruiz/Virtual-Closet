"""Integration tests for buyer link endpoints (bolt 029)."""

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
async def test_generate_buyer_link_requires_auth(client):
    """Unauthenticated requests to POST /buyer-links should return 401."""
    response = await client.post(
        "/api/tenants/buyer-links",
        json={"catalog_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_buyer_link_empty_catalog_ids(authenticated_client):
    """Empty catalog_ids should return 400."""
    response = await authenticated_client.post(
        "/api/tenants/buyer-links",
        json={"catalog_ids": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_buyer_link_success(authenticated_client):
    """Valid request should return a signed URL and expires_at."""
    catalog_id = str(uuid.uuid4())
    response = await authenticated_client.post(
        "/api/tenants/buyer-links",
        json={"catalog_ids": [catalog_id], "ttl_days": 30},
    )
    assert response.status_code == 201
    data = response.json()
    assert "signed_url" in data
    assert "expires_at" in data
    assert data["catalog_ids"] == [catalog_id]
    assert "/portal/access?token=" in data["signed_url"]


@pytest.mark.asyncio
async def test_list_buyer_links(authenticated_client):
    """GET /buyer-links should return list of links for tenant."""
    await authenticated_client.post(
        "/api/tenants/buyer-links",
        json={"catalog_ids": [str(uuid.uuid4())]},
    )

    response = await authenticated_client.get("/api/tenants/buyer-links")
    assert response.status_code == 200
    data = response.json()
    assert "links" in data
    assert len(data["links"]) >= 1


@pytest.mark.asyncio
async def test_validate_buyer_link_valid_token(authenticated_client):
    """Valid token should return valid: true with catalog_ids."""
    generate_response = await authenticated_client.post(
        "/api/tenants/buyer-links",
        json={"catalog_ids": [str(uuid.uuid4())]},
    )
    signed_url = generate_response.json()["signed_url"]
    token = signed_url.split("token=")[1]

    response = await authenticated_client.post(
        "/api/buyer-links/validate",
        json={"token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "tenant_id" in data
    assert "catalog_ids" in data


@pytest.mark.asyncio
async def test_validate_buyer_link_invalid_token(client):
    """Invalid token should return valid: false with reason."""
    response = await client.post(
        "/api/buyer-links/validate",
        json={"token": "invalid.jwt.token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["reason"] == "invalid_token"


@pytest.mark.asyncio
async def test_validate_buyer_link_empty_token(client):
    """Empty token should return valid: false."""
    response = await client.post(
        "/api/buyer-links/validate",
        json={"token": ""},
    )
    assert response.status_code == 422
