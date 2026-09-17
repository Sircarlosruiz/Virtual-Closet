import uuid
from unittest.mock import AsyncMock, create_autospec, patch

import pytest
from sqlalchemy import select

import core.database as database
from api.schemas.template import ImageTemplateUpdateRequest
from models.composition_snapshot import CompositionSnapshot
from models.generation_job import GenerationJob
from models.image_template import ImageTemplate, TemplateReference
from models.mayorista import Mayorista
from repositories.composition_snapshot_repo import (
    CompositionSnapshotAlreadyExistsError,
    CompositionSnapshotRepository,
)
from repositories.generation_job_repo import GenerationJobRepository
from repositories.image_template_repo import ImageTemplateRepository
from services.composition_snapshot_service import (
    CompositionSnapshotService,
    TemplateReferenceUnavailableError,
)
from services.image_generation_service import ImageGenerationService
from services.storage_service import StorageService
from services.template_lifecycle_service import TemplateLifecycleService
from tests.conftest import login_user, register_user


async def _promote_to_staff(email: str = "test@mayorista.com") -> None:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        user.role = "staff"
        await session.commit()


async def _get_owner_id(email: str = "test@mayorista.com") -> uuid.UUID:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        return user.id


async def _create_job_and_template(owner_id, reference_keys=("templates/ref-1.jpg",)):
    async with database.async_session() as session:
        job = GenerationJob(
            owner_id=owner_id,
            mode="text",
            provider="openai",
            status="completed",
            input_data={"mode": "text", "prompt": "a red jacket"},
        )
        template = ImageTemplate(
            scope="common",
            version=1,
            status="active",
            name="Studio look",
            background="white studio",
            prompt="clean composition",
            created_by=owner_id,
            references=[TemplateReference(storage_key=key) for key in reference_keys],
        )
        session.add_all([job, template])
        await session.commit()
        await session.refresh(job)
        await session.refresh(template, attribute_names=["references"])
        return job, template


def _make_service(db, storage_available=True):
    storage_service = create_autospec(StorageService, instance=True)
    storage_service.object_exists.return_value = storage_available
    snapshot_service = CompositionSnapshotService(
        CompositionSnapshotRepository(db),
        ImageGenerationService(GenerationJobRepository(db)),
        storage_service=storage_service,
    )
    return snapshot_service, storage_service


@pytest.mark.asyncio
async def test_capture_snapshot_freezes_configuration(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, storage = _make_service(db)
        snapshot = await service.capture_snapshot(job, template)

    assert snapshot.generation_job_id == job.id
    assert snapshot.template_id == template.id
    assert snapshot.template_version == 1
    config = snapshot.effective_configuration
    assert config["background"] == "white studio"
    assert config["prompt"] == "clean composition"
    assert config["provider"] == "openai"
    assert config["reference_keys"] == ["templates/ref-1.jpg"]
    storage.object_exists.assert_awaited_with("templates/ref-1.jpg", bucket_override="originals")


@pytest.mark.asyncio
async def test_capture_snapshot_fails_when_reference_missing(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db, storage_available=False)
        with pytest.raises(TemplateReferenceUnavailableError):
            await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        repo = CompositionSnapshotRepository(db)
        assert await repo.get_by_generation_job_id(job.id) is None


@pytest.mark.asyncio
async def test_capture_snapshot_twice_for_same_job_raises(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        with pytest.raises(CompositionSnapshotAlreadyExistsError):
            await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        count = len(
            (
                await db.execute(
                    select(CompositionSnapshot).where(
                        CompositionSnapshot.generation_job_id == job.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert count == 1


@pytest.mark.asyncio
async def test_snapshot_survives_template_edit_and_archive(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        lifecycle = TemplateLifecycleService(ImageTemplateRepository(db))
        await lifecycle.revise_template(
            template.id, ImageTemplateUpdateRequest(prompt="a completely different prompt")
        )
        await lifecycle.archive_template(template.id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        snapshot = await service.get_snapshot(job.id)

    assert snapshot.effective_configuration["prompt"] == "clean composition"
    assert snapshot.template_version == 1


@pytest.mark.asyncio
async def test_regenerate_creates_new_job_without_overwriting_original(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        snapshot = await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        new_job = await service.regenerate(job, snapshot)

    assert new_job.id != job.id
    assert new_job.mode == job.mode
    assert new_job.provider == job.provider
    assert new_job.input_data["prompt"] == job.input_data["prompt"]

    async with database.async_session() as db:
        original = await CompositionSnapshotRepository(db).get_by_generation_job_id(job.id)
        assert original.id == snapshot.id
        new_snapshot = await CompositionSnapshotRepository(db).get_by_generation_job_id(new_job.id)
        assert new_snapshot is None


@pytest.mark.asyncio
async def test_regenerate_fails_when_reference_missing(client):
    await register_user(client)
    await login_user(client)
    owner_id = await _get_owner_id()
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        snapshot = await service.capture_snapshot(job, template)

    async with database.async_session() as db:
        service, _ = _make_service(db, storage_available=False)
        with pytest.raises(TemplateReferenceUnavailableError):
            await service.regenerate(job, snapshot)

    async with database.async_session() as db:
        jobs = (await db.execute(select(GenerationJob))).scalars().all()
        assert len(jobs) == 1


@pytest.mark.asyncio
async def test_get_snapshot_endpoint_returns_404_before_capture(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _get_owner_id("staff@test.com")
    job, _template = await _create_job_and_template(owner_id)

    response = await client.get(f"/api/templates/snapshots/{job.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_snapshot_endpoint_is_ownership_scoped(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _get_owner_id("staff@test.com")
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        await service.capture_snapshot(job, template)

    owned = await client.get(f"/api/templates/snapshots/{job.id}")
    assert owned.status_code == 200
    assert owned.json()["generation_job_id"] == str(job.id)

    await register_user(client, email="other@test.com", nombre_negocio="Other Business")
    await login_user(client, email="other@test.com")
    await _promote_to_staff("other@test.com")

    missing = await client.get(f"/api/templates/snapshots/{job.id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_endpoint_dispatches_new_job(client):
    await register_user(client, email="staff@test.com")
    await login_user(client, email="staff@test.com")
    await _promote_to_staff("staff@test.com")
    owner_id = await _get_owner_id("staff@test.com")
    job, template = await _create_job_and_template(owner_id)

    async with database.async_session() as db:
        service, _ = _make_service(db)
        await service.capture_snapshot(job, template)

    with patch("api.routers.composition_snapshots.celery_app.send_task") as mock_send, patch(
        "services.composition_snapshot_service.StorageService"
    ) as mock_storage_cls:
        mock_storage_cls.return_value.object_exists = AsyncMock(return_value=True)
        response = await client.post(f"/api/templates/snapshots/{job.id}/regenerate")

    assert response.status_code == 202
    new_job_id = response.json()["job_id"]
    assert new_job_id != str(job.id)
    mock_send.assert_called_once_with("tasks.generate_image", args=[new_job_id])
