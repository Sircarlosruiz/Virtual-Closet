import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from models.customer import Customer
from services.token_service import TokenService
from tests.conftest import login_user, register_user


async def _register_customer(client, email="buyer@test.com", name="Test Buyer"):
    """Helper to register a customer and return the response."""
    response = await client.post(
        "/api/customers",
        json={"name": name, "email": email},
    )
    return response


# --- Story 001: Register Customer ---


@pytest.mark.asyncio
async def test_should_register_customer_when_authenticated(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await _register_customer(client, email="ana@buyer.com", name="Ana López")

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Ana López"
    assert data["email"] == "ana@buyer.com"
    assert data["status"] == "invited"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_should_reject_register_customer_without_auth(client):
    response = await _register_customer(client)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_reject_register_customer_with_invalid_email(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.post(
        "/api/customers",
        json={"name": "Ana", "email": "not-an-email"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_register_customer_with_empty_name(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.post(
        "/api/customers",
        json={"name": "", "email": "ana@buyer.com"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_duplicate_customer_email(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    await _register_customer(client, email="ana@buyer.com")
    response = await _register_customer(client, email="ana@buyer.com")

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_should_allow_same_email_for_different_mayoristas(client):
    await register_user(client, email="mayorista1@test.com", nombre_negocio="Business 1")
    await login_user(client, email="mayorista1@test.com")
    response1 = await _register_customer(client, email="ana@buyer.com")
    await client.post("/api/auth/logout")

    await register_user(client, email="mayorista2@test.com", nombre_negocio="Business 2")
    await login_user(client, email="mayorista2@test.com")
    response2 = await _register_customer(client, email="ana@buyer.com")

    assert response1.status_code == 201
    assert response2.status_code == 201


# --- Story 002: Buyer Portal Auth ---


@pytest.mark.asyncio
async def test_should_reject_invalid_token(client):
    response = await client.get("/api/portal/auth?token=invalid_token")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_reject_missing_token(client):
    response = await client.get("/api/portal/auth")
    assert response.status_code == 422


# --- Story 002: Magic Link ---


@pytest.mark.asyncio
async def test_should_request_magic_link_for_existing_customer(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")
    await _register_customer(client, email="ana@buyer.com")

    response = await client.post(
        "/api/portal/magic-link",
        json={"email": "ana@buyer.com"},
    )

    assert response.status_code == 200
    assert "magic link has been sent" in response.json()["message"]


@pytest.mark.asyncio
async def test_should_return_200_for_nonexistent_email(client):
    response = await client.post(
        "/api/portal/magic-link",
        json={"email": "nonexistent@buyer.com"},
    )

    assert response.status_code == 200
    assert "magic link has been sent" in response.json()["message"]


@pytest.mark.asyncio
async def test_should_reject_magic_link_with_invalid_email(client):
    response = await client.post(
        "/api/portal/magic-link",
        json={"email": "not-an-email"},
    )

    assert response.status_code == 422


# --- Story 003: Browse Published Catalogs ---


@pytest.mark.asyncio
async def test_should_reject_portal_access_without_buyer_session(client):
    response = await client.get("/api/portal/catalogs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_reject_portal_access_with_mayorista_session(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.get("/api/portal/catalogs")
    assert response.status_code == 401


# --- Security Tests ---


@pytest.mark.asyncio
async def test_mayorista_session_cannot_access_portal_endpoints(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.get("/api/portal/catalogs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_hash_never_exposed_in_responses(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await _register_customer(client, email="ana@buyer.com")

    assert response.status_code == 201
    data = response.json()
    assert "invitation_token_hash" not in data
    assert "token_hash" not in data
    assert "hash" not in str(data).lower()


# --- Story 004: List Customers ---


@pytest.mark.asyncio
async def test_should_list_customers(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    await _register_customer(client, email="ana@buyer.com", name="Ana López")
    await _register_customer(client, email="carlos@buyer.com", name="Carlos Ruiz")

    response = await client.get("/api/customers")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["customers"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_should_return_empty_list_when_no_customers(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.get("/api/customers")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["customers"] == []


@pytest.mark.asyncio
async def test_should_paginate_customer_list(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    for i in range(5):
        await _register_customer(client, email=f"buyer{i}@test.com", name=f"Buyer {i}")

    response = await client.get("/api/customers?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["customers"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_should_reject_list_customers_without_auth(client):
    response = await client.get("/api/customers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_only_list_own_customers(client):
    await register_user(client, email="mayorista1@test.com", nombre_negocio="Business 1")
    await login_user(client, email="mayorista1@test.com")
    await _register_customer(client, email="ana@buyer.com", name="Ana")
    await client.post("/api/auth/logout")

    await register_user(client, email="mayorista2@test.com", nombre_negocio="Business 2")
    await login_user(client, email="mayorista2@test.com")
    await _register_customer(client, email="carlos@buyer.com", name="Carlos")

    response = await client.get("/api/customers")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["customers"][0]["name"] == "Carlos"


@pytest.mark.asyncio
async def test_should_reject_invalid_page_size(client):
    await register_user(client, email="mayorista@test.com", nombre_negocio="Test Business")
    await login_user(client, email="mayorista@test.com")

    response = await client.get("/api/customers?page_size=0")
    assert response.status_code == 422

    response = await client.get("/api/customers?page_size=101")
    assert response.status_code == 422
