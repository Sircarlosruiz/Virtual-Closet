"""Cookie-staff lookup of explicit product links for the generation UI."""

import pytest

from tests.conftest import login_user, register_user
from tests.test_integration_bridge import _BridgeSetup


@pytest.mark.asyncio
async def test_should_return_role_on_me_when_authenticated(client):
    await register_user(client, email="role-me@test.com")
    await login_user(client, email="role-me@test.com")

    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "mayorista"


@pytest.mark.asyncio
async def test_should_resolve_product_link_when_staff_owns_tenant(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff("lookup-staff@test.com")
    link = await setup.create_product_link(
        tenant_id,
        staff.id,
        external_product_id="sku-lookup-1",
        external_wholesaler_id="wh-1",
    )
    await login_user(client, email="lookup-staff@test.com")

    response = await client.get(
        "/api/product-links/lookup",
        params={
            "system": "bfashion",
            "external_product_id": "sku-lookup-1",
            "external_wholesaler_id": "wh-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(link.id)
    assert body["external_product_id"] == "sku-lookup-1"
    assert body["external_wholesaler_id"] == "wh-1"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_should_reject_product_link_lookup_when_not_staff(client):
    await register_user(client, email="lookup-mayorista@test.com")
    await login_user(client, email="lookup-mayorista@test.com")

    response = await client.get(
        "/api/product-links/lookup",
        params={"external_product_id": "sku-x"},
    )
    assert response.status_code == 403
    assert "Staff access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_should_fail_closed_when_product_link_unknown(client):
    setup = _BridgeSetup(client)
    await setup.register_staff("lookup-missing@test.com")
    await login_user(client, email="lookup-missing@test.com")

    response = await client.get(
        "/api/product-links/lookup",
        params={"external_product_id": "does-not-exist"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_should_fail_closed_when_product_link_belongs_to_other_tenant(client):
    setup = _BridgeSetup(client)
    owner, tenant_id = await setup.register_staff("lookup-owner@test.com")
    await setup.create_product_link(
        tenant_id,
        owner.id,
        external_product_id="sku-other-tenant",
    )
    await setup.register_staff("lookup-other@test.com")
    await login_user(client, email="lookup-other@test.com")

    response = await client.get(
        "/api/product-links/lookup",
        params={"external_product_id": "sku-other-tenant"},
    )
    assert response.status_code == 403
    assert "different tenant" in response.json()["detail"]
