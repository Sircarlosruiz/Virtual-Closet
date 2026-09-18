import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

import core.database as database
from core.config import settings
from models.generation_job import GenerationJob
from models.mayorista import Mayorista
from tests.conftest import login_user, register_user


def _assert_no_secrets_leaked(payload: dict) -> None:
    serialized = json.dumps(payload).lower()
    assert "api_key" not in serialized
    assert "openai_api_key" not in serialized
    secret = settings.OPENAI_API_KEY.strip()
    if secret:
        assert secret not in json.dumps(payload)


def _assert_public_payload_hides_secrets(payload: dict) -> None:
    assert set(payload) == {"job_id", "mode", "provider", "status", "created_at"}
    _assert_no_secrets_leaked(payload)


def _assert_detail_payload_hides_secrets(payload: dict) -> None:
    assert set(payload) == {
        "job_id",
        "mode",
        "provider",
        "status",
        "created_at",
        "attempts",
        "usage",
        "preview_url",
    }
    _assert_no_secrets_leaked(payload)


async def _promote_to_staff(email: str = "test@mayorista.com") -> None:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        user.role = "staff"
        await session.commit()


@pytest.mark.asyncio
async def test_create_job_requires_staff_role(client):
    await register_user(client)
    await login_user(client)

    with patch("api.routers.image_generation.celery_app.send_task") as mock_send:
        response = await client.post(
            "/api/image-generation/jobs",
            json={"mode": "text", "prompt": "a jacket"},
        )
        mock_send.assert_not_called()

    assert response.status_code == 403
    assert response.json()["detail"] == "Staff access required"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected_provider",
    [
        ({"mode": "text", "prompt": "a red jacket"}, "openai"),
        (
            {
                "mode": "edit",
                "prompt": "replace background",
                "reference_image_ids": [str(uuid.uuid4())],
            },
            "openai",
        ),
        (
            {"mode": "extraction", "reference_image_ids": [str(uuid.uuid4())]},
            "openai",
        ),
        (
            {
                "mode": "try_on",
                "provider": "vton",
                "garment_id": str(uuid.uuid4()),
                "model_id": str(uuid.uuid4()),
                "cloth_type": "upper_body",
            },
            "vton",
        ),
    ],
)
async def test_staff_accepts_supported_mode_contracts(client, payload, expected_provider):
    await register_user(client)
    await login_user(client)
    await _promote_to_staff()

    with patch("api.routers.image_generation.celery_app.send_task") as mock_send:
        response = await client.post("/api/image-generation/jobs", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["mode"] == payload["mode"]
    assert data["provider"] == expected_provider
    assert "job_id" in data
    _assert_public_payload_hides_secrets(data)

    mock_send.assert_called_once_with("tasks.generate_image", args=[data["job_id"]])

    async with database.async_session() as session:
        job = (
            await session.execute(
                select(GenerationJob).where(GenerationJob.id == uuid.UUID(data["job_id"]))
            )
        ).scalar_one()
        assert job.status == "queued"
        assert job.provider == expected_provider
        serialized_input = json.dumps(job.input_data).lower()
        assert "api_key" not in serialized_input
        if settings.OPENAI_API_KEY.strip():
            assert settings.OPENAI_API_KEY not in json.dumps(job.input_data)


@pytest.mark.asyncio
async def test_get_job_is_owner_scoped_and_hides_secrets(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")

    with patch("api.routers.image_generation.celery_app.send_task"):
        created = await client.post(
            "/api/image-generation/jobs",
            json={"mode": "text", "prompt": "a jacket"},
        )
    job_id = created.json()["job_id"]

    owned = await client.get(f"/api/image-generation/jobs/{job_id}")
    assert owned.status_code == 200
    assert owned.json()["job_id"] == job_id
    assert owned.json()["attempts"] == []
    assert owned.json()["usage"] == {"status": "unknown", "model": None, "call_count": None}
    _assert_detail_payload_hides_secrets(owned.json())

    await register_user(client, email="other@test.com", nombre_negocio="Other Business")
    await login_user(client, email="other@test.com")

    missing = await client.get(f"/api/image-generation/jobs/{job_id}")
    assert missing.status_code == 404
