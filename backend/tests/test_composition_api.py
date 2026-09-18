import io
import uuid
from unittest.mock import patch

import pytest
from PIL import Image
from sqlalchemy import select

import core.database as database
from models.generation_job import GenerationJob
from models.mayorista import Mayorista
from tests.conftest import login_user, register_user


class ApiFakeStorage:
    objects: dict[str, bytes] = {}
    uploaded: list[str] = []

    def __init__(self) -> None:
        pass

    async def object_exists(self, key: str, bucket_override: str | None = None) -> bool:
        return key in ApiFakeStorage.objects

    async def get_object_bytes(
        self, key: str, bucket_override: str | None = None
    ) -> bytes:
        return ApiFakeStorage.objects[key]

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "image/jpeg",
        bucket_override: str | None = None,
    ) -> None:
        ApiFakeStorage.objects[key] = data
        ApiFakeStorage.uploaded.append(key)


def make_base(width: int = 600, height: int = 800) -> bytes:
    image = Image.new("RGB", (width, height), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def _promote_to_staff(email: str) -> None:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        user.role = "staff"
        await session.commit()


async def _owner_id(email: str) -> uuid.UUID:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        return user.id


async def _create_job(owner_id, result_key: str = "generated/base.png") -> GenerationJob:
    async with database.async_session() as session:
        job = GenerationJob(
            owner_id=owner_id,
            mode="text",
            provider="openai",
            status="completed",
            input_data={"mode": "text", "prompt": "a red jacket"},
            result_key=result_key,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


def _composition_body(sku: str = "REF: CAM-001", **style_overrides) -> dict:
    style = {"color": "#000000", "font_size": 48}
    style.update(style_overrides)
    return {
        "sku": sku,
        "placement": {"anchor": "bottom-right", "offset_x": 24, "offset_y": 24},
        "style": style,
    }


@pytest.fixture(autouse=True)
def reset_fake_storage():
    ApiFakeStorage.objects = {}
    ApiFakeStorage.uploaded = []
    yield


@pytest.mark.asyncio
async def test_non_staff_cannot_compose(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _owner_id("test@mayorista.com")
    job = await _create_job(owner_id)
    ApiFakeStorage.objects[job.result_key] = make_base()

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        response = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body()
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_compose_is_created_then_idempotent(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id)
    ApiFakeStorage.objects[job.result_key] = make_base()

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        created = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body()
        )
        repeated = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body()
        )

    assert created.status_code == 201, created.text
    assert created.json()["status"] == "valid"
    assert created.json()["sku"] == "REF: CAM-001"
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["id"] == created.json()["id"]


@pytest.mark.asyncio
async def test_compose_fit_failure_returns_structured_422(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id)
    ApiFakeStorage.objects[job.result_key] = make_base()
    body = {
        "sku": "REF: TOO-LONG-TO-FIT",
        "placement": {"max_width": 10, "max_height": 10},
        "style": {"color": "#000000", "font_size": 200},
    }

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        response = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=body
        )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "OVERLAY_DOES_NOT_FIT"
    assert detail["context"]["version_id"]


@pytest.mark.asyncio
async def test_composition_read_endpoints_and_ownership(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id)
    ApiFakeStorage.objects[job.result_key] = make_base()

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        created = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body()
        )
        version_id = created.json()["id"]
        summary = await client.get(f"/api/generation-jobs/{job.id}/composition")
        versions = await client.get(
            f"/api/generation-jobs/{job.id}/composition/versions"
        )
        single = await client.get(f"/api/composition-versions/{version_id}")

    assert summary.status_code == 200, summary.text
    assert summary.json()["latest_version"]["id"] == version_id
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert single.status_code == 200
    assert single.json()["id"] == version_id

    await register_user(client, email="other@test.com", nombre_negocio="Other Business")
    await login_user(client, email="other@test.com")
    await _promote_to_staff("other@test.com")

    hidden = await client.get(f"/api/composition-versions/{version_id}")
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_composition_unknown_job_is_404(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        response = await client.get(f"/api/generation-jobs/{uuid.uuid4()}/composition")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compose_rejects_blank_sku_and_unknown_font(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id)
    ApiFakeStorage.objects[job.result_key] = make_base()

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        blank_sku = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body(sku=" ")
        )
        unknown_font = await client.post(
            f"/api/generation-jobs/{job.id}/composition",
            json=_composition_body(font_family="comic-sans"),
        )

    assert blank_sku.status_code == 400, blank_sku.text
    assert unknown_font.status_code == 400, unknown_font.text


@pytest.mark.asyncio
async def test_compose_without_completed_base_image_is_409(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id, result_key=None)

    with patch("services.sku_composition_service.StorageService", ApiFakeStorage):
        response = await client.post(
            f"/api/generation-jobs/{job.id}/composition", json=_composition_body()
        )

    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_reads_return_404_without_overlay_or_version(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _owner_id("staff@test.com")
    job = await _create_job(owner_id)

    summary = await client.get(f"/api/generation-jobs/{job.id}/composition")
    versions = await client.get(f"/api/generation-jobs/{job.id}/composition/versions")
    unknown_version = await client.get(f"/api/composition-versions/{uuid.uuid4()}")

    assert summary.status_code == 404
    assert versions.status_code == 404
    assert unknown_version.status_code == 404
