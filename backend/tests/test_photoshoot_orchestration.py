"""Tick, materialization, and publication-candidate tests for bolt 053."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select

import core.database as database
from models.generation_job import GenerationJob
from models.media import MediaItem
from models.photoshoot import Photoshoot, PhotoshootResult
from models.publication import PublicationSelection
from repositories.generation_job_repo import GenerationJobRepository
from repositories.photoshoot_repo import PhotoshootRepository
from services.photoshoot_materialization_service import PhotoshootMaterializationService
from services.photoshoot_orchestration_service import PhotoshootOrchestrationService
from services.sku_composition_service import OverlayDoesNotFitError
from services.vton_job_service import PhotoOwnershipError
from tests.test_photoshoot_submission import (
    SEND_TASK,
    _post_photoshoot,
    _setup_ready,
    _submit_body,
)
def _job(status="complete", output_key="media/extracted/out.png"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        output_minio_key=output_key if status == "complete" else None,
    )


def _pose_set_pair():
    pose_set = SimpleNamespace(id=uuid.uuid4())
    batch = SimpleNamespace(id=uuid.uuid4(), status="complete", items=[])
    return pose_set, batch


def _complete_item(model_photo_id: uuid.UUID, media_id: uuid.UUID):
    return SimpleNamespace(
        model_id=model_photo_id,
        status="complete",
        result_media_id=media_id,
    )


async def _build_tick_service(db, **overrides):
    repo = PhotoshootRepository(db)
    jobs = GenerationJobRepository(db)
    storage = overrides.get("storage") or MagicMock()
    storage.object_exists = AsyncMock(return_value=False)
    storage.get_object_bytes = AsyncMock(return_value=b"png-bytes")
    storage.upload_bytes = AsyncMock()
    batch_submit = MagicMock()
    batch_submit.publish_pending = MagicMock()
    service = PhotoshootOrchestrationService(
        db=db,
        repo=repo,
        tryoff=overrides.get("tryoff") or MagicMock(submit_job=AsyncMock(return_value=_job())),
        tryoff_jobs=overrides.get("tryoff_jobs") or MagicMock(get_by_id=AsyncMock()),
        vton=overrides.get("vton")
        or MagicMock(validate_pairing=AsyncMock(return_value=None)),
        poses=overrides.get("poses")
        or MagicMock(submit=AsyncMock(return_value=_pose_set_pair())),
        batches=overrides.get("batches")
        or MagicMock(get_by_id_and_mayorista=AsyncMock(return_value=None)),
        batch_submit=batch_submit,
        media=overrides.get("media") or MagicMock(get_by_id=AsyncMock(return_value=None)),
        garments=overrides.get("garments")
        or MagicMock(get_by_minio_key=AsyncMock(return_value=None)),
        garment_upload=overrides.get("garment_upload")
        or MagicMock(
            register_existing_garment=AsyncMock(
                return_value=SimpleNamespace(id=uuid.uuid4())
            )
        ),
        materializer=overrides.get("materializer")
        or PhotoshootMaterializationService(repo, jobs, storage),
        composition=overrides.get("composition")
        or MagicMock(compose=AsyncMock()),
        overlays=overrides.get("overlays")
        or MagicMock(get_by_generation_job_id=AsyncMock(return_value=None)),
        storage=storage,
    )
    return service


async def _load(photoshoot_id: uuid.UUID) -> Photoshoot:
    async with database.async_session() as session:
        return await PhotoshootRepository(session).get(photoshoot_id)


@pytest.mark.asyncio
async def test_tick_runs_tryoff_then_vton_then_pose_sets(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, n_models=2)
    response, _ = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    tryoff_job = _job(status="pending")
    tryoff = MagicMock(submit_job=AsyncMock(return_value=tryoff_job))
    tryoff_jobs = MagicMock(get_by_id=AsyncMock(return_value=tryoff_job))
    vton = MagicMock(validate_pairing=AsyncMock(return_value=None))
    poses = MagicMock(submit=AsyncMock(return_value=_pose_set_pair()))

    async with database.async_session() as session:
        service = await _build_tick_service(
            session, tryoff=tryoff, tryoff_jobs=tryoff_jobs, vton=vton, poses=poses
        )
        assert await service.tick(photoshoot_id) == "reschedule"
        tryoff.submit_job.assert_awaited_once()
        assert tryoff.submit_job.await_args.kwargs["commit"] is False
        assert tryoff.submit_job.await_args.kwargs["publish"] is False
        tryoff.publish_job.assert_called_once_with(tryoff_job.id)
        vton.validate_pairing.assert_not_awaited()

    tryoff_job.status = "complete"
    tryoff_job.output_minio_key = "media/extracted/out.png"
    async with database.async_session() as session:
        service = await _build_tick_service(
            session, tryoff=tryoff, tryoff_jobs=tryoff_jobs, vton=vton, poses=poses
        )
        await service.tick(photoshoot_id)
        assert vton.validate_pairing.await_count == 2
        assert poses.submit.await_count == 2

    row = await _load(photoshoot_id)
    stages = {stage.name: stage.status for stage in row.stages}
    assert stages["tryoff"] == "completed"
    assert stages["vton"] == "completed"
    assert stages["poses"] == "running"


@pytest.mark.asyncio
async def test_tick_keeps_other_branches_when_one_vton_fails(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, n_models=2, kind="flat_garment")
    response, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    failing = str(ctx.models[0].id)

    async def _validate(mayorista_id, garment_id, photo_id, cloth_type=None):
        row = await _load(photoshoot_id)
        photo = row.configuration["resolved_poses"][failing][0]["model_photo_id"]
        if str(photo_id) == photo:
            raise PhotoOwnershipError("no")

    media_id = uuid.uuid4()
    living = ctx.models[1]
    living_photo = None
    row = await _load(photoshoot_id)
    living_photo = uuid.UUID(
        row.configuration["resolved_poses"][str(living.id)][0]["model_photo_id"]
    )
    batch = SimpleNamespace(
        id=uuid.uuid4(),
        status="complete",
        items=[_complete_item(living_photo, media_id)],
    )
    poses = MagicMock(submit=AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), batch)))
    media = MagicMock(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(minio_key="media/result.png")
        )
    )
    batches = MagicMock(get_by_id_and_mayorista=AsyncMock(return_value=batch))

    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            vton=MagicMock(validate_pairing=AsyncMock(side_effect=_validate)),
            poses=poses,
            batches=batches,
            media=media,
        )
        await service.tick(photoshoot_id)

    row = await _load(photoshoot_id)
    assert row.status == "partial"
    assert poses.submit.await_count == 1
    assert len(row.results) == 1
    assert row.results[0].model_id == living.id


@pytest.mark.asyncio
async def test_tick_fails_when_every_vton_branch_fails(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, n_models=2, kind="flat_garment")
    response, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    poses = MagicMock(submit=AsyncMock())
    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            vton=MagicMock(
                validate_pairing=AsyncMock(side_effect=PhotoOwnershipError("no"))
            ),
            poses=poses,
        )
        outcome = await service.tick(photoshoot_id)
    row = await _load(photoshoot_id)
    assert outcome == "done"
    assert row.status == "failed"
    assert {stage.name: stage.status for stage in row.stages}["vton"] == "failed"
    poses.submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_tick_stops_after_tryoff_failure(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, _ = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    failed = _job(status="failed")
    poses = MagicMock(submit=AsyncMock())
    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            tryoff=MagicMock(submit_job=AsyncMock(return_value=failed)),
            tryoff_jobs=MagicMock(get_by_id=AsyncMock(return_value=failed)),
            poses=poses,
        )
        await service.tick(photoshoot_id)
        await service.tick(photoshoot_id)
    row = await _load(photoshoot_id)
    assert row.status == "failed"
    assert row.error_code == "TRYOFF_FAILED"
    poses.submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_materialize_nine_completed_jobs(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, n_models=3, kind="flat_garment")
    response, _ = await _post_photoshoot(
        client, ctx, _submit_body(ctx, input_kind="flat_garment")
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    row = await _load(photoshoot_id)
    media_rows = []
    batches_by_model: dict[str, SimpleNamespace] = {}
    async with database.async_session() as session:
        for model_id, poses in row.configuration["resolved_poses"].items():
            items = []
            for item in poses:
                media = MediaItem(
                    mayorista_id=row.mayorista_id,
                    tenant_id=row.tenant_id,
                    minio_key=f"media/{item['model_photo_id']}.png",
                    media_type="vton_result",
                    filename="pose.png",
                    content_type="image/png",
                    size_bytes=4,
                )
                session.add(media)
                await session.flush()
                media_rows.append(media)
                items.append(
                    _complete_item(uuid.UUID(item["model_photo_id"]), media.id)
                )
            batches_by_model[model_id] = SimpleNamespace(
                id=uuid.uuid4(), status="complete", items=items
            )
        await session.commit()

    async def _submit(mayorista_id, tenant_id, garment_id, model_id, cloth_type, pose_ids):
        batch = batches_by_model[str(model_id)]
        return SimpleNamespace(id=uuid.uuid4()), batch

    async def _get_batch(batch_id, mayorista_id):
        for batch in batches_by_model.values():
            if batch.id == batch_id:
                return batch
        return None

    media_by_id = {media.id: media for media in media_rows}

    async def _get_media(item_id, mayorista_id):
        return media_by_id.get(item_id)

    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            vton=MagicMock(validate_pairing=AsyncMock(return_value=None)),
            poses=MagicMock(submit=AsyncMock(side_effect=_submit)),
            batches=MagicMock(get_by_id_and_mayorista=AsyncMock(side_effect=_get_batch)),
            media=MagicMock(get_by_id=AsyncMock(side_effect=_get_media)),
        )
        await service.tick(photoshoot_id)

    async with database.async_session() as session:
        jobs = (await session.execute(select(GenerationJob))).scalars().all()
        results = (await session.execute(select(PhotoshootResult))).scalars().all()
        photoshoot = await PhotoshootRepository(session).get(photoshoot_id)
        selections = (await session.execute(select(PublicationSelection))).scalars().all()
    assert len(jobs) == 9
    assert len(results) == 9
    assert all(job.status == "completed" and job.result_key for job in jobs)
    assert all(job.owner_id == ctx.owner for job in jobs)
    assert all(
        job.result_key.startswith(f"photoshoots/{photoshoot_id}/") for job in jobs
    )
    assert photoshoot.status == "completed"
    assert selections == []


@pytest.mark.asyncio
async def test_duplicate_tick_does_not_create_tenth_job(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    response, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    row = await _load(photoshoot_id)
    photo_id = uuid.UUID(
        row.configuration["resolved_poses"][str(ctx.models[0].id)][0]["model_photo_id"]
    )
    async with database.async_session() as session:
        media = MediaItem(
            mayorista_id=row.mayorista_id,
            tenant_id=row.tenant_id,
            minio_key="media/one.png",
            media_type="vton_result",
            filename="one.png",
            content_type="image/png",
            size_bytes=3,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        media_id = media.id
    batch = SimpleNamespace(
        id=uuid.uuid4(),
        status="complete",
        items=[_complete_item(photo_id, media_id)],
    )
    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            poses=MagicMock(
                submit=AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), batch))
            ),
            batches=MagicMock(get_by_id_and_mayorista=AsyncMock(return_value=batch)),
            media=MagicMock(
                get_by_id=AsyncMock(
                    return_value=SimpleNamespace(minio_key="media/one.png")
                )
            ),
        )
        await service.tick(photoshoot_id)
        await service.tick(photoshoot_id)
    async with database.async_session() as session:
        count = (
            await session.execute(select(func.count()).select_from(GenerationJob))
        ).scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_copy_failure_does_not_complete_job(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    storage = MagicMock()
    storage.object_exists = AsyncMock(return_value=False)
    storage.get_object_bytes = AsyncMock(side_effect=RuntimeError("minio down"))
    storage.upload_bytes = AsyncMock()
    async with database.async_session() as session:
        repo = PhotoshootRepository(session)
        photoshoot = Photoshoot(
            product_link_id=uuid.UUID(ctx.link_id),
            staff_id=ctx.owner,
            source_image_id=uuid.UUID(ctx.source_id),
            tenant_id=ctx.tenant_id,
            mayorista_id=ctx.owner,
            input_kind="flat_garment",
            configuration={},
            status="running",
            expected_results=1,
        )
        session.add(photoshoot)
        await session.flush()
        materializer = PhotoshootMaterializationService(
            repo, GenerationJobRepository(session), storage
        )
        stored = await materializer.materialize_slot(
            photoshoot,
            model_id=ctx.models[0].id,
            pose_id=uuid.uuid4(),
            pose="front",
            source_key="media/src.png",
        )
        await session.commit()
        photoshoot_id = photoshoot.id
    assert stored is None
    async with database.async_session() as session:
        jobs = (await session.execute(select(GenerationJob))).scalars().all()
        results = (
            await session.execute(
                select(PhotoshootResult).where(
                    PhotoshootResult.photoshoot_id == photoshoot_id
                )
            )
        ).scalars().all()
    assert jobs == []
    assert results == []


@pytest.mark.asyncio
async def test_overlay_fit_failure_keeps_base_job_as_candidate(
    client, monkeypatch, preview_urls, fake_bfashion
):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    response, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(
            ctx,
            input_kind="flat_garment",
            pose_ids=["front"],
            overlay={"text": "sku-largo"},
        ),
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    row = await _load(photoshoot_id)
    photo_id = uuid.UUID(
        row.configuration["resolved_poses"][str(ctx.models[0].id)][0]["model_photo_id"]
    )
    async with database.async_session() as session:
        media = MediaItem(
            mayorista_id=row.mayorista_id,
            tenant_id=row.tenant_id,
            minio_key="media/base.png",
            media_type="vton_result",
            filename="base.png",
            content_type="image/png",
            size_bytes=4,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        media_id = media.id
    batch = SimpleNamespace(
        id=uuid.uuid4(),
        status="complete",
        items=[_complete_item(photo_id, media_id)],
    )
    async with database.async_session() as session:
        service = await _build_tick_service(
            session,
            poses=MagicMock(
                submit=AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), batch))
            ),
            batches=MagicMock(get_by_id_and_mayorista=AsyncMock(return_value=batch)),
            media=MagicMock(
                get_by_id=AsyncMock(
                    return_value=SimpleNamespace(minio_key="media/base.png")
                )
            ),
            composition=MagicMock(
                compose=AsyncMock(
                    side_effect=OverlayDoesNotFitError("too wide", uuid.uuid4())
                )
            ),
        )
        await service.tick(photoshoot_id)
    row = await _load(photoshoot_id)
    job_id = row.results[0].generation_job_id
    with patch(SEND_TASK):
        candidates = await client.get(
            f"/api/integration/v1/products/draft-1/generation-jobs/{job_id}/publication-candidates",
            headers=ctx.headers,
        )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()[0]["generation_job_id"] == str(job_id)
    published = await client.post(
        "/api/integration/v1/products/draft-1/publications",
        json={
            "staff_id": ctx.staff_id,
            "generation_job_id": str(job_id),
            "decision": "selected",
        },
        headers=ctx.headers,
    )
    assert published.status_code == 201, published.text
    destinations = {row["destination"] for row in published.json()["deliveries"]}
    assert "virtual_closet" in destinations


@pytest.mark.asyncio
async def test_restarted_tick_does_not_resubmit_completed_tryoff(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, _ = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    photoshoot_id = uuid.UUID(response.json()["photoshoot_id"])
    tryoff_job = _job(status="complete")
    tryoff = MagicMock(submit_job=AsyncMock(return_value=tryoff_job))
    tryoff_jobs = MagicMock(get_by_id=AsyncMock(return_value=tryoff_job))
    async with database.async_session() as session:
        first = await _build_tick_service(
            session, tryoff=tryoff, tryoff_jobs=tryoff_jobs
        )
        await first.tick(photoshoot_id)
    async with database.async_session() as session:
        second = await _build_tick_service(
            session, tryoff=tryoff, tryoff_jobs=tryoff_jobs
        )
        await second.tick(photoshoot_id)
    assert tryoff.submit_job.await_count == 1


def test_celery_task_reschedules_when_tick_returns_reschedule(monkeypatch):
    from tasks.photoshoot_orchestration import photoshoot_tick_task

    async def _reschedule(_photoshoot_id):
        return "reschedule"

    monkeypatch.setattr("tasks.photoshoot_orchestration._tick", _reschedule)
    photoshoot_id = str(uuid.uuid4())
    with patch.object(photoshoot_tick_task, "apply_async") as reschedule:
        photoshoot_tick_task.run(photoshoot_id)
    reschedule.assert_called_once()
    assert reschedule.call_args.kwargs["args"] == [photoshoot_id]
