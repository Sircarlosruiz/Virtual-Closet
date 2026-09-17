import uuid

import pytest
from sqlalchemy import select

import core.database as database
from models.mayorista import Mayorista
from tests.conftest import login_user, register_user


async def _promote_to_staff(email: str = "test@mayorista.com") -> None:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        user.role = "staff"
        await session.commit()


async def _staff_client(client, email="test@mayorista.com"):
    await register_user(client, email=email)
    await login_user(client, email=email)
    await _promote_to_staff(email)


async def _register_wholesaler(client, email: str) -> uuid.UUID:
    """Creates a mayorista row (FK target for `wholesaler_id`) without logging in as it."""
    await register_user(client, email=email, nombre_negocio="Wholesaler")
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        return user.id


@pytest.mark.asyncio
async def test_create_template_requires_staff_role(client):
    await register_user(client)
    await login_user(client)

    response = await client.post(
        "/api/templates", json={"scope": "common", "name": "Studio backdrop"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Staff access required"


@pytest.mark.asyncio
async def test_create_common_template(client):
    await _staff_client(client)

    response = await client.post(
        "/api/templates",
        json={
            "scope": "common",
            "name": "Studio backdrop",
            "background": "white studio",
            "references": [{"storage_key": "templates/ref-1.jpg", "label": "front"}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["scope"] == "common"
    assert data["wholesaler_id"] is None
    assert data["version"] == 1
    assert data["status"] == "draft"
    assert len(data["references"]) == 1
    assert data["references"][0]["storage_key"] == "templates/ref-1.jpg"


@pytest.mark.asyncio
async def test_private_template_requires_wholesaler_id(client):
    await _staff_client(client)

    response = await client.post(
        "/api/templates", json={"scope": "private", "name": "Wholesaler-only look"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_private_template_only_selectable_by_assigned_wholesaler(client):
    await _staff_client(client)

    wholesaler_a = await _register_wholesaler(client, "wholesaler-a@test.com")
    wholesaler_b = await _register_wholesaler(client, "wholesaler-b@test.com")

    common = await client.post(
        "/api/templates", json={"scope": "common", "name": "Common look"}
    )
    assert common.status_code == 201

    private = await client.post(
        "/api/templates",
        json={
            "scope": "private",
            "wholesaler_id": str(wholesaler_a),
            "name": "Wholesaler A look",
        },
    )
    assert private.status_code == 201
    private_id = private.json()["id"]

    selectable_a = await client.get(
        "/api/templates/selectable", params={"wholesaler_id": str(wholesaler_a)}
    )
    assert selectable_a.status_code == 200
    ids_a = {t["id"] for t in selectable_a.json()}
    assert private_id in ids_a
    assert common.json()["id"] in ids_a

    selectable_b = await client.get(
        "/api/templates/selectable", params={"wholesaler_id": str(wholesaler_b)}
    )
    assert selectable_b.status_code == 200
    ids_b = {t["id"] for t in selectable_b.json()}
    assert private_id not in ids_b
    assert common.json()["id"] in ids_b


@pytest.mark.asyncio
async def test_revise_template_increments_version(client):
    await _staff_client(client)

    created = await client.post(
        "/api/templates", json={"scope": "common", "name": "Studio backdrop"}
    )
    template_id = created.json()["id"]
    assert created.json()["version"] == 1

    revised = await client.patch(
        f"/api/templates/{template_id}", json={"prompt": "clean white background"}
    )
    assert revised.status_code == 200
    assert revised.json()["version"] == 2
    assert revised.json()["prompt"] == "clean white background"


@pytest.mark.asyncio
async def test_revising_archived_template_is_rejected(client):
    await _staff_client(client)

    created = await client.post(
        "/api/templates", json={"scope": "common", "name": "Studio backdrop"}
    )
    template_id = created.json()["id"]

    archived = await client.post(f"/api/templates/{template_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    revised = await client.patch(f"/api/templates/{template_id}", json={"prompt": "new prompt"})
    assert revised.status_code == 409


@pytest.mark.asyncio
async def test_archived_template_excluded_from_selection_but_still_readable(client):
    await _staff_client(client)

    wholesaler_id = await _register_wholesaler(client, "wholesaler-c@test.com")
    created = await client.post(
        "/api/templates",
        json={"scope": "private", "wholesaler_id": str(wholesaler_id), "name": "Look"},
    )
    template_id = created.json()["id"]

    await client.post(f"/api/templates/{template_id}/archive")

    selectable = await client.get(
        "/api/templates/selectable", params={"wholesaler_id": str(wholesaler_id)}
    )
    assert template_id not in {t["id"] for t in selectable.json()}

    detail = await client.get(f"/api/templates/{template_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_get_nonexistent_template_returns_404(client):
    await _staff_client(client)

    response = await client.get(f"/api/templates/{uuid.uuid4()}")
    assert response.status_code == 404
