import uuid

import pytest

from tests.conftest import login_user, register_user


@pytest.mark.asyncio
async def test_should_create_catalog_when_authenticated(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.post(
        "/api/catalogos",
        json={"name": "Summer Collection 2026"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Summer Collection 2026"
    assert data["status"] == "draft"
    assert data["item_count"] == 0
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_should_reject_create_catalog_with_empty_name(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.post(
        "/api/catalogos",
        json={"name": ""},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_create_catalog_with_whitespace_only_name(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.post(
        "/api/catalogos",
        json={"name": "   "},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_create_catalog_with_name_too_long(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    long_name = "A" * 101
    response = await client.post(
        "/api/catalogos",
        json={"name": long_name},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_create_catalog_without_auth(client):
    response = await client.post(
        "/api/catalogos",
        json={"name": "Summer Collection"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_create_multiple_catalogs_for_same_mayorista(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response1 = await client.post(
        "/api/catalogos",
        json={"name": "Collection 1"},
    )
    response2 = await client.post(
        "/api/catalogos",
        json={"name": "Collection 2"},
    )

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["id"] != response2.json()["id"]


@pytest.mark.asyncio
async def test_should_trim_whitespace_from_catalog_name(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.post(
        "/api/catalogos",
        json={"name": "  Summer Collection  "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Summer Collection"


@pytest.mark.asyncio
async def test_should_allow_duplicate_catalog_names(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response1 = await client.post(
        "/api/catalogos",
        json={"name": "Same Name"},
    )
    response2 = await client.post(
        "/api/catalogos",
        json={"name": "Same Name"},
    )

    assert response1.status_code == 201
    assert response2.status_code == 201


async def _create_catalog(client, name="Test Catalog"):
    response = await client.post("/api/catalogos", json={"name": name})
    return response.json()


# --- Story 005: Rename Catalog ---


@pytest.mark.asyncio
async def test_should_rename_catalog(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client, "Old Name")

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={"name": "New Name"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_should_reject_rename_with_empty_name(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client)

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={"name": "   "},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_reject_rename_nonexistent_catalog(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.patch(
        f"/api/catalogos/{uuid.uuid4()}",
        json={"name": "New Name"},
    )

    assert response.status_code == 404


# --- Story 006: Publish/Unpublish Catalog ---


@pytest.mark.asyncio
async def test_should_reject_publish_empty_catalog(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client)

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={"status": "published"},
    )

    assert response.status_code == 422
    assert "empty catalog" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_should_reject_invalid_status_value(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client)

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={"status": "archived"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_update_both_name_and_status(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client, "Old Name")

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={"name": "New Name", "status": "draft"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_should_reject_update_without_fields(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client)

    response = await client.patch(
        f"/api/catalogos/{catalog['id']}",
        json={},
    )

    assert response.status_code == 400


# --- Story 007: Delete Catalog ---


@pytest.mark.asyncio
async def test_should_delete_catalog(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    catalog = await _create_catalog(client)

    response = await client.delete(f"/api/catalogos/{catalog['id']}")
    assert response.status_code == 204

    list_response = await client.get("/api/catalogos")
    assert list_response.json()["total"] == 0


@pytest.mark.asyncio
async def test_should_reject_delete_nonexistent_catalog(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.delete(f"/api/catalogos/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_should_reject_delete_without_auth(client):
    response = await client.delete(f"/api/catalogos/{uuid.uuid4()}")
    assert response.status_code == 401


# --- Story 008: List Catalogs ---


@pytest.mark.asyncio
async def test_should_list_catalogs(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    await _create_catalog(client, "Catalog 1")
    await _create_catalog(client, "Catalog 2")
    await _create_catalog(client, "Catalog 3")

    response = await client.get("/api/catalogos")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["catalogs"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_should_return_empty_list_when_no_catalogs(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.get("/api/catalogos")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["catalogs"] == []


@pytest.mark.asyncio
async def test_should_paginate_catalog_list(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    for i in range(5):
        await _create_catalog(client, f"Catalog {i}")

    response = await client.get("/api/catalogos?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["catalogs"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_should_reject_list_without_auth(client):
    response = await client.get("/api/catalogos")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_only_list_own_catalogs(client):
    await register_user(client, email="user1@test.com", nombre_negocio="User 1")
    await login_user(client, email="user1@test.com")
    await _create_catalog(client, "User 1 Catalog")
    await client.post("/api/auth/logout")

    await register_user(client, email="user2@test.com", nombre_negocio="User 2")
    await login_user(client, email="user2@test.com")
    await _create_catalog(client, "User 2 Catalog")

    response = await client.get("/api/catalogos")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["catalogs"][0]["name"] == "User 2 Catalog"


@pytest.mark.asyncio
async def test_should_reject_invalid_page_size(client):
    await register_user(client, email="catalog@test.com", nombre_negocio="Catalog Test")
    await login_user(client, email="catalog@test.com")

    response = await client.get("/api/catalogos?page_size=0")
    assert response.status_code == 422

    response = await client.get("/api/catalogos?page_size=101")
    assert response.status_code == 422
