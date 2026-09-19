"""Contract tests for bolt 051 — source-image presign, confirm, and rejection."""

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

import core.database as database
from models.bridge_source_image import BridgeSourceImage
from models.media import GarmentPhoto
from models.tryoff_job import SourceImage
from tests.test_bridge_provisioning import _provision
from tests.test_integration_bridge import _BridgeSetup

JPEG = b"\xff\xd8\xff" + b"x" * 97
PNG = b"\x89PNG" + b"x" * 96
STORAGE = "services.source_image_intake_service.StorageService"


def _assert_no_secrets(payload: dict) -> None:
    serialized = json.dumps(payload).lower()
    assert "password" not in serialized
    assert "secret" not in serialized
    assert "minioadmin" not in serialized
    assert "api_key" not in serialized


async def _bridge_product(client, external_product_id: str = "draft-1"):
    setup = _BridgeSetup(client)
    _registrar, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    staff_id = (await _provision(client, setup, service_client, secret)).json()[
        "staff_id"
    ]
    created = await client.post(
        "/api/integration/v1/product-links",
        json={"external_product_id": external_product_id, "staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    assert created.status_code == 201, created.text
    return setup, service_client, secret, staff_id, created.json()["product_link_id"]


def _presign_body(staff_id, **overrides):
    body = {
        "staff_id": staff_id,
        "kind": "garment_on_model",
        "content_type": "image/jpeg",
        "size_bytes": len(JPEG),
        "filename": "look.jpg",
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_should_presign_put_when_staff_and_link_are_valid(client):
    setup, service_client, secret, staff_id, link_id = await _bridge_product(
        client
    )
    upload_url = "https://minio.test/put?X-Amz-Signature=abc"

    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = upload_url
        response = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )

    assert response.status_code == 201, response.text
    data = response.json()
    uuid.UUID(data["source_image_id"])
    assert data["method"] == "PUT"
    assert data["upload_url"] == upload_url
    assert data["headers"]["Content-Type"] == "image/jpeg"
    assert data["expires_in"] == 900
    assert data["storage_key"] == (
        f"bridge/source-images/{link_id}/{data['source_image_id']}"
    )
    _assert_no_secrets(data)

    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(data["source_image_id"])
                )
            )
        ).scalar_one()
        assert row.status == "pending"
        assert str(row.product_link_id) == link_id


@pytest.mark.asyncio
async def test_should_reject_invalid_content_type_before_signing(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        response = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, content_type="image/gif"),
            headers=setup.headers(service_client, secret),
        )
    assert response.status_code == 422
    sign.assert_not_called()
    async with database.async_session() as session:
        rows = (await session.execute(select(BridgeSourceImage))).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_should_reject_oversized_declaration_before_signing(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        response = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, size_bytes=11 * 1024 * 1024),
            headers=setup.headers(service_client, secret),
        )
    assert response.status_code == 422
    sign.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_unknown_kind_before_signing(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    response = await client.post(
        "/api/integration/v1/products/draft-1/source-images:presign",
        json=_presign_body(staff_id, kind="on_hanger"),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_should_return_404_when_product_link_is_missing(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    response = await client.post(
        "/api/integration/v1/products/missing/source-images:presign",
        json=_presign_body(staff_id),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"


@pytest.mark.asyncio
async def test_should_forbid_revoked_staff_on_presign_and_confirm(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    revoked = await client.post(
        "/api/integration/v1/staff-identities/42:revoke",
        headers=setup.headers(service_client, secret),
    )
    assert revoked.status_code == 200

    presign = await client.post(
        "/api/integration/v1/products/draft-1/source-images:presign",
        json=_presign_body(staff_id),
        headers=setup.headers(service_client, secret),
    )
    assert presign.status_code == 403
    assert presign.json()["detail"]["code"] == "STAFF_FORBIDDEN"

    confirm = await client.post(
        f"/api/integration/v1/products/draft-1/source-images/{uuid.uuid4()}:confirm",
        json={"staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    assert confirm.status_code == 403
    assert confirm.json()["detail"]["code"] == "STAFF_FORBIDDEN"


@pytest.mark.asyncio
async def test_should_reject_presign_without_service_headers(client):
    response = await client.post(
        "/api/integration/v1/products/draft-1/source-images:presign",
        json=_presign_body(str(uuid.uuid4())),
    )
    assert response.status_code == 401
    assert response.json()["detail"] in {
        "Unauthorized",
        "Invalid service credentials",
    }


@pytest.mark.asyncio
async def test_should_keep_filename_out_of_storage_key(client):
    setup, service_client, secret, staff_id, link_id = await _bridge_product(
        client
    )
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        response = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, filename="../../etc/passwd.jpg"),
            headers=setup.headers(service_client, secret),
        )
    assert response.status_code == 201, response.text
    key = response.json()["storage_key"]
    assert ".." not in key
    assert "passwd" not in key
    assert key.startswith(f"bridge/source-images/{link_id}/")


@pytest.mark.asyncio
async def test_should_confirm_garment_on_model_as_source_image(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        preview.return_value = "https://minio.test/get"
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert confirm.status_code == 200, confirm.text
    data = confirm.json()
    assert data["status"] == "ready"
    assert data["kind"] == "garment_on_model"
    assert data["content_type"] == "image/jpeg"
    assert data["size_bytes"] == len(JPEG)
    assert data["preview_url"] == "https://minio.test/get"
    _assert_no_secrets(data)

    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(source_image_id)
                )
            )
        ).scalar_one()
        assert row.status == "ready"
        assert row.registered_media_kind == "source_image"
        media = (
            await session.execute(
                select(SourceImage).where(SourceImage.id == row.registered_media_id)
            )
        ).scalar_one()
        assert media.minio_key == row.storage_key


@pytest.mark.asyncio
async def test_should_confirm_flat_garment_as_garment_photo(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(
                staff_id,
                kind="flat_garment",
                content_type="image/png",
                size_bytes=len(PNG),
                filename="flat.png",
            ),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {"content_type": "image/png", "content_length": len(PNG)}
        get_bytes.return_value = PNG
        preview.return_value = "https://minio.test/get"
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert confirm.status_code == 200, confirm.text
    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(source_image_id)
                )
            )
        ).scalar_one()
        assert row.registered_media_kind == "garment_photo"
        photo = (
            await session.execute(
                select(GarmentPhoto).where(GarmentPhoto.id == row.registered_media_id)
            )
        ).scalar_one()
        assert photo.minio_key == row.storage_key


@pytest.mark.asyncio
async def test_should_replay_ready_confirm_without_second_media(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        preview.return_value = "https://minio.test/get"
        first = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )
        second = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["source_image_id"] == second.json()["source_image_id"]
    async with database.async_session() as session:
        media = (await session.execute(select(SourceImage))).scalars().all()
        assert len(media) == 1


@pytest.mark.asyncio
async def test_should_keep_pending_when_object_is_missing(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head:
        head.return_value = None
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert confirm.status_code == 409
    assert confirm.json()["detail"]["code"] == "SOURCE_IMAGE_NOT_UPLOADED"
    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(source_image_id)
                )
            )
        ).scalar_one()
        assert row.status == "pending"


@pytest.mark.asyncio
async def test_should_reject_when_declared_type_does_not_match_bytes(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, content_type="image/jpeg", size_bytes=len(PNG)),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
    ):
        head.return_value = {"content_type": "image/png", "content_length": len(PNG)}
        get_bytes.return_value = PNG
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert confirm.status_code == 409
    assert confirm.json()["detail"]["code"] == "SOURCE_IMAGE_REJECTED"
    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(source_image_id)
                )
            )
        ).scalar_one()
        assert row.status == "rejected"
        assert row.rejection_reason == "CONTENT_TYPE_MISMATCH"

    again = await client.post(
        f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
        json={"staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "SOURCE_IMAGE_REJECTED"


@pytest.mark.asyncio
async def test_should_reject_checksum_mismatch(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={
                "staff_id": staff_id,
                "checksum_sha256": "0" * 64,
            },
            headers=setup.headers(service_client, secret),
        )
    assert confirm.status_code == 409
    assert confirm.json()["detail"]["context"]["reason"] == "CHECKSUM_MISMATCH"


@pytest.mark.asyncio
async def test_should_accept_matching_checksum(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]
    digest = hashlib.sha256(JPEG).hexdigest()

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        preview.return_value = "https://minio.test/get"
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id, "checksum_sha256": digest},
            headers=setup.headers(service_client, secret),
        )
    assert confirm.status_code == 200, confirm.text


@pytest.mark.asyncio
async def test_should_return_same_403_for_missing_and_foreign_source_image(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(
        client, "draft-1"
    )
    other = await client.post(
        "/api/integration/v1/product-links",
        json={"external_product_id": "draft-2", "staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    assert other.status_code == 201

    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        foreign = await client.post(
            "/api/integration/v1/products/draft-2/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    foreign_id = foreign.json()["source_image_id"]

    missing = await client.post(
        f"/api/integration/v1/products/draft-1/source-images/{uuid.uuid4()}:confirm",
        json={"staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    stolen = await client.post(
        f"/api/integration/v1/products/draft-1/source-images/{foreign_id}:confirm",
        json={"staff_id": staff_id},
        headers=setup.headers(service_client, secret),
    )
    assert missing.status_code == 403
    assert stolen.status_code == 403
    assert missing.json()["detail"]["code"] == "SOURCE_IMAGE_FORBIDDEN"
    assert stolen.json() == missing.json()


@pytest.mark.asyncio
async def test_should_hide_product_from_other_tenant(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    other_setup = _BridgeSetup(client)
    _other_staff, other_tenant = await other_setup.register_staff(
        email="other@test.com"
    )
    other_client, other_secret = await other_setup.create_service_client(
        other_tenant, system="bfashion-b"
    )
    other_staff_id = (
        await _provision(
            client,
            other_setup,
            other_client,
            other_secret,
            external_staff_id="99",
            email="mirror-other@example.com",
        )
    ).json()["staff_id"]

    response = await client.post(
        "/api/integration/v1/products/draft-1/source-images:presign",
        json=_presign_body(other_staff_id),
        headers=other_setup.headers(other_client, other_secret),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"


@pytest.mark.asyncio
async def test_should_return_404_when_product_link_is_inactive(client):
    setup, service_client, secret, staff_id, link_id = await _bridge_product(client)
    from models.product_link import ProductLink

    async with database.async_session() as session:
        product = (
            await session.execute(
                select(ProductLink).where(ProductLink.id == uuid.UUID(link_id))
            )
        ).scalar_one()
        product.is_active = False
        await session.commit()

    response = await client.post(
        "/api/integration/v1/products/draft-1/source-images:presign",
        json=_presign_body(staff_id),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"


@pytest.mark.asyncio
async def test_should_reject_empty_or_unreadable_object(client):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        empty_presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, size_bytes=3),
            headers=setup.headers(service_client, secret),
        )
        garbage_presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id, size_bytes=8, filename="x.jpg"),
            headers=setup.headers(service_client, secret),
        )
    empty_id = empty_presign.json()["source_image_id"]
    garbage_id = garbage_presign.json()["source_image_id"]

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
    ):
        head.return_value = {"content_type": "image/jpeg", "content_length": 0}
        get_bytes.return_value = b""
        empty = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{empty_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )
        head.return_value = {"content_type": "image/jpeg", "content_length": 8}
        get_bytes.return_value = b"notimg!!"
        garbage = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{garbage_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert empty.status_code == 409
    assert empty.json()["detail"]["context"]["reason"] == "OBJECT_EMPTY"
    assert garbage.status_code == 409
    assert garbage.json()["detail"]["context"]["reason"] == "UNREADABLE_IMAGE"
    _assert_no_secrets(empty.json())
    _assert_no_secrets(garbage.json())


@pytest.mark.asyncio
async def test_should_reject_when_actual_object_exceeds_limit(client, monkeypatch):
    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]
    monkeypatch.setattr(
        "services.source_image_intake_service.settings.BRIDGE_SOURCE_IMAGE_MAX_BYTES",
        50,
    )

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_image_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )

    assert confirm.status_code == 409
    detail = confirm.json()["detail"]
    assert detail["code"] == "SOURCE_IMAGE_REJECTED"
    assert detail["context"]["reason"] == "OBJECT_TOO_LARGE"
    _assert_no_secrets(confirm.json())
    async with database.async_session() as session:
        row = (
            await session.execute(
                select(BridgeSourceImage).where(
                    BridgeSourceImage.id == uuid.UUID(source_image_id)
                )
            )
        ).scalar_one()
        assert row.status == "rejected"
        assert row.actual_size_bytes == len(JPEG)


@pytest.mark.asyncio
async def test_should_register_one_media_under_concurrent_confirm(client):
    import asyncio

    setup, service_client, secret, staff_id, _link = await _bridge_product(client)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(staff_id),
            headers=setup.headers(service_client, secret),
        )
    source_image_id = presign.json()["source_image_id"]
    url = (
        f"/api/integration/v1/products/draft-1/source-images/"
        f"{source_image_id}:confirm"
    )

    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {
            "content_type": "image/jpeg",
            "content_length": len(JPEG),
        }
        get_bytes.return_value = JPEG
        preview.return_value = "https://minio.test/get"
        first, second = await asyncio.gather(
            client.post(
                url,
                json={"staff_id": staff_id},
                headers=setup.headers(service_client, secret),
            ),
            client.post(
                url,
                json={"staff_id": staff_id},
                headers=setup.headers(service_client, secret),
            ),
        )

    assert {first.status_code, second.status_code} == {200}
    assert first.json()["source_image_id"] == second.json()["source_image_id"]
    async with database.async_session() as session:
        media = (await session.execute(select(SourceImage))).scalars().all()
        assert len(media) == 1
