"""Bolt 054 — aggregate GET, idempotency replay, variant_key (stories 004-006)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

import core.database as database
from api.schemas.publication import PublicationCandidateResponse
from models.generation_job import GenerationJob
from models.media import MediaItem
from models.photoshoot import Photoshoot
from models.publication import PublicationSelection
from services.idempotency_service import compute_payload_fingerprint
from services.photoshoot_idempotency_service import photoshoot_fingerprint_payload
from services.photoshoot_status import counters, view_status
from tests.test_photoshoot_orchestration import (
    _build_tick_service,
    _complete_item,
    _load,
)
from tests.test_photoshoot_submission import (
    SEND_TASK,
    _assert_no_secrets,
    _post_photoshoot,
    _setup_ready,
    _submit_body,
)
from tests.test_source_image_intake import _bridge_product

VIEW = "/api/integration/v1/products/{pid}/photoshoots/{sid}"


def test_should_fingerprint_ignore_json_key_order():
    staff = uuid.uuid4()
    source = uuid.uuid4()
    model = uuid.uuid4()
    first = photoshoot_fingerprint_payload(
        staff_id=staff,
        source_image_id=source,
        input_kind="flat_garment",
        template_id=None,
        model_ids=[model],
        pose_ids=["side", "front"],
        pose_count=None,
        cloth_type="upper_body",
        background=None,
        colors=None,
        overlay=None,
        variant_key=None,
        external_wholesaler_id=None,
    )
    second = dict(reversed(list(first.items())))
    assert compute_payload_fingerprint(first) == compute_payload_fingerprint(second)
    assert first["pose_ids"] == ["front", "side"]


def test_should_keep_queued_when_stages_pending():
    stages = [
        SimpleNamespace(name="tryoff", status="skipped"),
        SimpleNamespace(name="vton", status="pending"),
        SimpleNamespace(name="poses", status="pending"),
        SimpleNamespace(name="composition", status="skipped"),
    ]
    assert view_status(stages=stages, expected_results=3, completed_results=0) == "queued"


def test_should_keep_running_when_a_live_stage_is_running():
    stages = [
        SimpleNamespace(name="tryoff", status="skipped"),
        SimpleNamespace(name="vton", status="running"),
        SimpleNamespace(name="poses", status="pending"),
        SimpleNamespace(name="composition", status="skipped"),
    ]
    assert view_status(stages=stages, expected_results=3, completed_results=0) == "running"


def test_should_mark_partial_when_idle_with_some_results():
    stages = [
        SimpleNamespace(name="tryoff", status="skipped"),
        SimpleNamespace(name="vton", status="completed"),
        SimpleNamespace(name="poses", status="completed"),
        SimpleNamespace(name="composition", status="skipped"),
    ]
    assert view_status(stages=stages, expected_results=3, completed_results=1) == "partial"


def test_should_mark_failed_when_idle_with_zero_results():
    stages = [
        SimpleNamespace(name="tryoff", status="failed"),
        SimpleNamespace(name="vton", status="failed"),
        SimpleNamespace(name="poses", status="failed"),
        SimpleNamespace(name="composition", status="skipped"),
    ]
    assert view_status(stages=stages, expected_results=3, completed_results=0) == "failed"


def test_should_not_count_blocked_overlay_as_failed_result():
    stages = [
        SimpleNamespace(name="tryoff", status="skipped", external_refs=[]),
        SimpleNamespace(name="vton", status="completed", external_refs=[]),
        SimpleNamespace(name="poses", status="completed", external_refs=[]),
        SimpleNamespace(
            name="composition",
            status="completed",
            error_code="COMPOSITION_BLOCKED",
            external_refs=[],
        ),
    ]
    tally = counters(
        expected_results=1,
        completed_results=1,
        stages=stages,
        configuration={"pose_types": ["front"]},
    )
    assert tally.failed_results == 0


@pytest.mark.asyncio
async def test_should_return_queued_view_without_candidates(
    client, monkeypatch, preview_urls
):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    created, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = created.json()["photoshoot_id"]
    response = await client.get(
        VIEW.format(pid=ctx.product, sid=photoshoot_id),
        headers=ctx.headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    _assert_no_secrets(data)
    assert data["status"] == "queued"
    assert data["expected_results"] == 1
    assert data["completed_results"] == 0
    assert data["failed_results"] == 0
    assert data["candidates"] == []
    assert data["results"] == []
    assert data["variant_key"] is None
    assert {
        "status",
        "stages",
        "expected_results",
        "completed_results",
        "failed_results",
        "results",
        "candidates",
    }.issubset(data)
    assert {row["name"]: row["status"] for row in data["stages"]}["tryoff"] == "skipped"
    with patch(SEND_TASK) as send:
        again = await client.get(
            VIEW.format(pid=ctx.product, sid=photoshoot_id),
            headers=ctx.headers,
        )
    assert again.status_code == 200
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_return_404_for_missing_and_foreign_photoshoot(
    client, monkeypatch
):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    created, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = created.json()["photoshoot_id"]
    missing = await client.get(
        VIEW.format(pid=ctx.product, sid=uuid.uuid4()),
        headers=ctx.headers,
    )
    other = await client.post(
        "/api/integration/v1/product-links",
        json={"external_product_id": "draft-2", "staff_id": ctx.staff_id},
        headers=ctx.headers,
    )
    assert other.status_code == 201, other.text
    foreign = await client.get(
        VIEW.format(pid="draft-2", sid=photoshoot_id),
        headers=ctx.headers,
    )
    unknown_product = await client.get(
        VIEW.format(pid="missing-product", sid=photoshoot_id),
        headers=ctx.headers,
    )
    assert missing.status_code == 404
    assert foreign.status_code == 404
    assert unknown_product.status_code == 404
    assert missing.json()["detail"]["code"] == "PHOTOSHOOT_NOT_FOUND"
    assert foreign.json()["detail"] == missing.json()["detail"]
    assert unknown_product.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"


@pytest.mark.asyncio
async def test_should_return_identical_401_on_view_without_service_headers(client):
    response = await client.get(VIEW.format(pid="draft-1", sid=uuid.uuid4()))
    assert response.status_code == 401
    assert response.json()["detail"] in {
        "Unauthorized",
        "Invalid service credentials",
    }


@pytest.mark.asyncio
async def test_should_conflict_when_idempotency_payload_changes(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    body = _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"])
    first, _ = await _post_photoshoot(
        client, ctx, body, **{"Idempotency-Key": "k1"}
    )
    changed = dict(body)
    changed["pose_ids"] = ["side"]
    second, send = await _post_photoshoot(
        client, ctx, changed, **{"Idempotency-Key": "k1"}
    )
    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_not_relaunch_failed_photoshoot_on_replay(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    body = _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"])
    first, _ = await _post_photoshoot(
        client, ctx, body, **{"Idempotency-Key": "fail-key"}
    )
    photoshoot_id = uuid.UUID(first.json()["photoshoot_id"])
    async with database.async_session() as session:
        row = await session.get(Photoshoot, photoshoot_id)
        row.status = "failed"
        row.error_code = "TRYOFF_FAILED"
        await session.commit()
    second, send = await _post_photoshoot(
        client, ctx, body, **{"Idempotency-Key": "fail-key"}
    )
    assert second.status_code == 202
    assert second.json()["photoshoot_id"] == str(photoshoot_id)
    assert second.json()["status"] == "failed"
    assert second.json()["created"] is False
    send.assert_not_called()


@pytest.mark.asyncio
async def test_unprotected_posts_create_two_photoshoots(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    body = _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"])
    first, _ = await _post_photoshoot(client, ctx, body)
    second, _ = await _post_photoshoot(client, ctx, body)
    assert first.json()["photoshoot_id"] != second.json()["photoshoot_id"]


async def _tick_one_result(photoshoot_id: uuid.UUID, ctx) -> None:
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
                submit=AsyncMock(
                    return_value=(SimpleNamespace(id=uuid.uuid4()), batch)
                )
            ),
            batches=MagicMock(
                get_by_id_and_mayorista=AsyncMock(return_value=batch)
            ),
            media=MagicMock(
                get_by_id=AsyncMock(
                    return_value=SimpleNamespace(minio_key="media/one.png")
                )
            ),
        )
        await service.tick(photoshoot_id)


@pytest.mark.asyncio
async def test_should_return_completed_view_with_candidate_schema(
    client, monkeypatch, preview_urls
):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    created, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(
            ctx,
            input_kind="flat_garment",
            pose_ids=["front"],
            variant_key="navy",
        ),
    )
    photoshoot_id = uuid.UUID(created.json()["photoshoot_id"])
    await _tick_one_result(photoshoot_id, ctx)

    view = await client.get(
        VIEW.format(pid=ctx.product, sid=photoshoot_id),
        headers=ctx.headers,
    )
    assert view.status_code == 200, view.text
    data = view.json()
    assert data["status"] == "completed"
    assert data["completed_results"] == 1
    assert data["failed_results"] == 0
    assert data["variant_key"] == "navy"
    assert data["results"][0]["variant_key"] == "navy"
    assert "minio_key" not in str(data["results"][0]["preview_url"])
    assert data["results"][0]["preview_url"].startswith("https://preview.test/")
    candidate = PublicationCandidateResponse.model_validate(data["candidates"][0])
    assert candidate.kind == "generation_result"
    job_id = data["results"][0]["generation_job_id"]
    listed = await client.get(
        f"/api/integration/v1/products/draft-1/generation-jobs/{job_id}/publication-candidates",
        headers=ctx.headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["generation_job_id"] == data["candidates"][0]["generation_job_id"]
    async with database.async_session() as session:
        selections = (
            await session.execute(select(PublicationSelection))
        ).scalars().all()
    assert selections == []


@pytest.mark.asyncio
async def test_two_variant_jobs_do_not_collide_on_publication_unique(
    client, fake_bfashion, preview_urls
):
    setup, service_client, secret, staff_id, link_id = await _bridge_product(
        client, "draft-1"
    )
    headers = setup.headers(service_client, secret)
    owner = uuid.UUID(staff_id)
    jobs = []
    async with database.async_session() as session:
        for index in range(2):
            job = GenerationJob(
                owner_id=owner,
                mode="try_on",
                provider="replicate",
                status="completed",
                input_data={"variant": index},
                result_key=f"photoshoots/job-{index}.png",
            )
            session.add(job)
            jobs.append(job)
        await session.commit()
        for job in jobs:
            await session.refresh(job)

    first = await client.post(
        "/api/integration/v1/products/draft-1/publications",
        json={
            "staff_id": staff_id,
            "generation_job_id": str(jobs[0].id),
            "decision": "selected",
        },
        headers=headers,
    )
    second = await client.post(
        "/api/integration/v1/products/draft-1/publications",
        json={
            "staff_id": staff_id,
            "generation_job_id": str(jobs[1].id),
            "decision": "selected",
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]


@pytest.mark.asyncio
async def test_bfashion_sync_failure_does_not_drop_generation_result(
    client, monkeypatch, fake_bfashion, preview_urls
):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    created, _ = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    photoshoot_id = uuid.UUID(created.json()["photoshoot_id"])
    await _tick_one_result(photoshoot_id, ctx)
    row = await _load(photoshoot_id)
    job_id = row.results[0].generation_job_id
    async with database.async_session() as session:
        job = await session.get(GenerationJob, job_id)
        stored_key = job.result_key
    fake_bfashion.fail = True
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
    by_dest = {item["destination"]: item for item in published.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "failed"
    retry = await client.post(
        f"/api/integration/v1/products/draft-1/publications/{published.json()['id']}/retry",
        headers=ctx.headers,
    )
    assert retry.status_code == 200, retry.text
    retry_dest = {item["destination"]: item for item in retry.json()["deliveries"]}
    assert retry_dest["virtual_closet"]["status"] == "synced"
    assert retry_dest["bfashion"]["status"] == "failed"
    async with database.async_session() as session:
        job = await session.get(GenerationJob, job_id)
        assert job.result_key == stored_key
        assert (
            await session.execute(
                select(Photoshoot).where(Photoshoot.id == photoshoot_id)
            )
        ).scalar_one() is not None
