"""Contract tests for bolt 056 — photoshoot options catalog (FR-16)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

import core.database as database
from models.image_template import ImageTemplate
from models.media import ModelPhoto
from models.model import Model
from models.product_link import ProductLink
from services.photoshoot_catalog_service import compute_catalog_version
from tests.test_integration_bridge import _BridgeSetup
from tests.test_source_image_intake import _bridge_product

PRESIGNED_URL = "https://minio.test/preview?X-Amz-Signature=abc"
OPTIONS = "/api/integration/v1/products/{pid}/photoshoot-options"
MINIO_PRESIGN = "core.minio_client.MinIOClient.get_presigned_url"


def _assert_no_secrets(payload: dict) -> None:
    serialized = json.dumps(payload).lower()
    assert "password" not in serialized
    assert "secret" not in serialized
    assert "minioadmin" not in serialized
    assert "api_key" not in serialized
    assert "storage_key" not in serialized
    assert "minio_key" not in serialized
    assert "prompt" not in serialized


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _insert_template(
    *,
    created_by: uuid.UUID,
    name: str,
    status: str = "active",
    scope: str = "common",
    wholesaler_id: uuid.UUID | None = None,
    background: str | None = "studio white",
    colors=None,
    version: int = 1,
) -> ImageTemplate:
    async with database.async_session() as session:
        template = ImageTemplate(
            scope=scope,
            wholesaler_id=wholesaler_id,
            version=version,
            status=status,
            name=name,
            background=background,
            colors=colors,
            created_by=created_by,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template


async def _insert_model(
    mayorista_id: uuid.UUID,
    name: str,
    poses: list[str],
    tenant_id: uuid.UUID | None = None,
) -> Model:
    async with database.async_session() as session:
        model = Model(mayorista_id=mayorista_id, name=name)
        session.add(model)
        await session.flush()
        for pose in poses:
            session.add(
                ModelPhoto(
                    mayorista_id=mayorista_id,
                    tenant_id=tenant_id,
                    model_id=model.id,
                    pose=pose,
                    minio_key=f"models/{model.id}/{pose}.jpg",
                    label=f"{name} {pose}",
                    content_type="image/jpeg",
                    size_bytes=12,
                )
            )
        await session.commit()
        await session.refresh(model)
        return model


@pytest.fixture
def mock_presign():
    with patch(MINIO_PRESIGN, new_callable=AsyncMock) as mocked:
        mocked.return_value = PRESIGNED_URL
        yield mocked


def test_should_change_catalog_version_when_visible_template_is_removed():
    t1 = SimpleNamespace(
        id=uuid.uuid4(),
        version=1,
        updated_at=_now(),
        scope="common",
    )
    t2 = SimpleNamespace(
        id=uuid.uuid4(),
        version=2,
        updated_at=_now(),
        scope="common",
    )
    first = compute_catalog_version([t1, t2], [], {})
    second = compute_catalog_version([t1], [], {})
    assert first != second
    assert first.startswith("sha256:")
    assert compute_catalog_version([t1, t2], [], {}) == first


def test_should_change_catalog_version_when_pose_is_added():
    model_id = uuid.uuid4()
    model = SimpleNamespace(id=model_id)
    photo = SimpleNamespace(
        id=uuid.uuid4(),
        pose="front",
        model_id=model_id,
        uploaded_at=_now(),
    )
    empty = compute_catalog_version([], [model], {model_id: []})
    with_pose = compute_catalog_version([], [model], {model_id: [photo]})
    assert empty != with_pose


@pytest.mark.asyncio
async def test_should_return_aggregated_catalog_for_active_link(client, mock_presign):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    owner = uuid.UUID(staff_id)
    common = await _insert_template(
        created_by=owner, name="Common look", colors=["#111111"]
    )
    await _insert_template(
        created_by=owner,
        name="Private look",
        scope="private",
        wholesaler_id=owner,
        background="warehouse",
        colors=None,
    )
    await _insert_template(
        created_by=owner, name="Draft look", status="draft"
    )
    await _insert_template(
        created_by=owner, name="Archived look", status="archived"
    )
    three = await _insert_model(
        owner, "Ana", ["front", "side", "back"], service_client.tenant_id
    )
    empty = await _insert_model(owner, "Bea", [], service_client.tenant_id)

    response = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    names = {item["name"] for item in data["templates"]}
    assert names == {"Common look", "Private look"}
    assert common.id.hex in {item["id"].replace("-", "") for item in data["templates"]}
    private_row = next(item for item in data["templates"] if item["name"] == "Private look")
    assert private_row["scope"] == "private"
    assert private_row["wholesaler_scope"] == staff_id
    assert private_row["colors"] is None
    assert data["cloth_types"] == [
        {"value": "upper_body", "label": "Upper body"},
        {"value": "lower_body", "label": "Lower body"},
        {"value": "dress", "label": "Dress"},
    ]
    assert data["max_pose_count"] == 3
    assert data["background_suggestions"] == ["studio white", "warehouse"]
    assert data["color_suggestions"] == ["#111111"]
    models = {item["name"]: item for item in data["models"]}
    assert models["Ana"]["available_poses"] == ["front", "side", "back"]
    assert models["Ana"]["preview_url"] == PRESIGNED_URL
    assert models["Bea"]["available_poses"] == []
    assert models["Bea"]["preview_url"] is None
    assert data["catalog_version"].startswith("sha256:")
    assert response.headers["etag"] == f'W/"{data["catalog_version"]}"'
    assert response.headers["cache-control"] == "private, no-cache"
    _assert_no_secrets(data)
    mock_presign.assert_called()
    assert str(three.id) in {item["id"] for item in data["models"]}
    assert str(empty.id) in {item["id"] for item in data["models"]}


@pytest.mark.asyncio
async def test_should_hide_foreign_private_templates_and_models(client, mock_presign):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    owner = uuid.UUID(staff_id)
    other = _BridgeSetup(client)
    foreign, _tenant = await other.register_staff(email="other-owner@test.com")
    await _insert_template(created_by=owner, name="Visible common")
    await _insert_template(
        created_by=foreign.id,
        name="Foreign private",
        scope="private",
        wholesaler_id=foreign.id,
    )
    await _insert_model(foreign.id, "Foreign model", ["front"], foreign.tenant_id)

    response = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )

    assert response.status_code == 200
    data = response.json()
    assert {item["name"] for item in data["templates"]} == {"Visible common"}
    assert data["models"] == []


@pytest.mark.asyncio
async def test_should_return_200_when_owner_has_no_private_assets(client, mock_presign):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    await _insert_template(created_by=uuid.UUID(staff_id), name="Only common")

    response = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["name"] for item in data["templates"]] == ["Only common"]
    assert data["models"] == []
    mock_presign.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_missing_service_headers_without_catalog(client):
    response = await client.get(OPTIONS.format(pid="draft-1"))
    assert response.status_code == 401
    assert "templates" not in response.text


@pytest.mark.asyncio
async def test_should_return_same_404_for_missing_inactive_and_cross_tenant(
    client, mock_presign
):
    setup, service_client, secret, staff_id, link_id = await _bridge_product(
        client, external_product_id="owned-1"
    )
    other = _BridgeSetup(client)
    _staff_b, tenant_b = await other.register_staff(email="tenant-b@test.com")
    client_b, secret_b = await other.create_service_client(tenant_b, system="bfashion-b")

    missing = await client.get(
        OPTIONS.format(pid="unknown"),
        headers=setup.headers(service_client, secret),
    )
    cross = await client.get(
        OPTIONS.format(pid="owned-1"),
        headers=other.headers(client_b, secret_b),
    )

    async with database.async_session() as session:
        link = (
            await session.execute(
                select(ProductLink).where(ProductLink.id == uuid.UUID(link_id))
            )
        ).scalar_one()
        link.is_active = False
        await session.commit()

    inactive = await client.get(
        OPTIONS.format(pid="owned-1"),
        headers=setup.headers(service_client, secret),
    )

    for response in (missing, cross, inactive):
        assert response.status_code == 404, response.text
        assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"
        assert "templates" not in response.text
    mock_presign.assert_not_called()


@pytest.mark.asyncio
async def test_should_return_404_when_wholesaler_id_mismatches(client, mock_presign):
    setup = _BridgeSetup(client)
    _registrar, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    from tests.test_bridge_provisioning import _provision

    staff_id = (await _provision(client, setup, service_client, secret)).json()[
        "staff_id"
    ]
    created = await client.post(
        "/api/integration/v1/product-links",
        json={
            "external_product_id": "draft-w",
            "staff_id": staff_id,
            "external_wholesaler_id": "wholesaler-a",
        },
        headers=setup.headers(service_client, secret),
    )
    assert created.status_code == 201

    response = await client.get(
        OPTIONS.format(pid="draft-w"),
        params={"external_wholesaler_id": "wholesaler-b"},
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"


@pytest.mark.asyncio
async def test_should_return_304_when_if_none_match_matches(client, mock_presign):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    await _insert_template(created_by=uuid.UUID(staff_id), name="Stable")

    first = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )
    assert first.status_code == 200
    version = first.json()["catalog_version"]
    mock_presign.reset_mock()

    second = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers={
            **setup.headers(service_client, secret),
            "If-None-Match": first.headers["etag"],
        },
    )
    assert second.status_code == 304
    assert second.content == b""
    assert second.headers["etag"] == f'W/"{version}"'
    mock_presign.assert_not_called()


@pytest.mark.asyncio
async def test_should_ignore_unknown_if_none_match(client, mock_presign):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    await _insert_template(created_by=uuid.UUID(staff_id), name="Stable")

    response = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers={
            **setup.headers(service_client, secret),
            "If-None-Match": 'W/"sha256:deadbeef"',
        },
    )
    assert response.status_code == 200
    assert response.json()["templates"]


@pytest.mark.asyncio
async def test_should_change_etag_when_active_template_is_archived(
    client, mock_presign
):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    owner = uuid.UUID(staff_id)
    kept = await _insert_template(created_by=owner, name="Kept")
    doomed = await _insert_template(created_by=owner, name="Doomed")

    first = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )
    old_version = first.json()["catalog_version"]

    async with database.async_session() as session:
        template = (
            await session.execute(
                select(ImageTemplate).where(ImageTemplate.id == doomed.id)
            )
        ).scalar_one()
        template.status = "archived"
        await session.commit()

    second = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )
    assert second.status_code == 200
    assert second.json()["catalog_version"] != old_version
    assert {item["name"] for item in second.json()["templates"]} == {"Kept"}
    assert str(kept.id) in {item["id"] for item in second.json()["templates"]}

    stale = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers={
            **setup.headers(service_client, secret),
            "If-None-Match": first.headers["etag"],
        },
    )
    assert stale.status_code == 200


@pytest.mark.asyncio
async def test_should_change_catalog_version_when_model_is_added(
    client, mock_presign
):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    owner = uuid.UUID(staff_id)
    await _insert_template(created_by=owner, name="Common")

    first = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )
    await _insert_model(owner, "New face", ["side"], service_client.tenant_id)
    second = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )

    assert first.json()["models"] == []
    assert [item["name"] for item in second.json()["models"]] == ["New face"]
    assert first.json()["catalog_version"] != second.json()["catalog_version"]
    assert second.json()["models"][0]["available_poses"] == ["side"]


@pytest.mark.asyncio
async def test_should_keep_serving_catalog_after_staff_revocation(
    client, mock_presign
):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    await _insert_template(created_by=uuid.UUID(staff_id), name="Still visible")
    revoked = await client.post(
        "/api/integration/v1/staff-identities/42:revoke",
        headers=setup.headers(service_client, secret),
    )
    assert revoked.status_code == 200

    response = await client.get(
        OPTIONS.format(pid="draft-1"),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 200
    assert response.json()["templates"]


@pytest.mark.asyncio
async def test_should_reject_empty_external_product_id(client):
    setup, service_client, secret, _staff, _link = await _bridge_product(client)
    response = await client.get(
        "/api/integration/v1/products/%20/photoshoot-options",
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code in {404, 422}


@pytest.mark.asyncio
async def test_should_complete_ten_concurrent_catalog_reads(client, mock_presign):
    import asyncio
    import time

    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    await _insert_template(created_by=uuid.UUID(staff_id), name="Hot path")

    async def _one():
        started = time.perf_counter()
        response = await client.get(
            OPTIONS.format(pid="draft-1"),
            headers=setup.headers(service_client, secret),
        )
        return response, time.perf_counter() - started

    results = await asyncio.gather(*[_one() for _ in range(10)])
    assert all(response.status_code == 200 for response, _ in results)
    versions = {response.json()["catalog_version"] for response, _ in results}
    assert len(versions) == 1
    # Local ASGI correctness, not a production p95 measurement.
    assert max(elapsed for _, elapsed in results) < 5
