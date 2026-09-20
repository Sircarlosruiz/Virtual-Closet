"""Contract tests for bolt 053 — photoshoot submit (stories 001)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import select

import core.database as database
from api.schemas.integration import PhotoshootCreateRequest
from core.config import settings
from models.photoshoot import Photoshoot, PhotoshootStage
from models.publication import PublicationSelection
from services.composition_spec import SKU_MAX_LENGTH
from services.photoshoot_pipeline_policy import plan
from services.photoshoot_status import derive
from tests.test_integration_bridge import _BridgeSetup
from tests.test_photoshoot_catalog import _insert_model, _insert_template
from tests.test_source_image_intake import (
    JPEG,
    PNG,
    STORAGE,
    _bridge_product,
    _presign_body,
)

SEND_TASK = "services.photoshoot_submission_service.celery_app.send_task"
PHOTOSHOOTS = "/api/integration/v1/products/{pid}/photoshoots"


def _assert_no_secrets(payload: dict) -> None:
    serialized = json.dumps(payload).lower()
    assert "password" not in serialized
    assert "secret" not in serialized
    assert "minioadmin" not in serialized
    assert "api_key" not in serialized
    assert "r8-" not in serialized


def test_should_plan_skipped_tryoff_for_flat_garment():
    stages = plan("flat_garment", has_overlay=False)
    assert [(s.name, s.status) for s in stages] == [
        ("tryoff", "skipped"),
        ("vton", "pending"),
        ("poses", "pending"),
        ("composition", "skipped"),
    ]


def test_should_plan_all_pending_when_on_model_with_overlay():
    stages = plan("garment_on_model", has_overlay=True)
    assert [s.status for s in stages] == ["pending", "pending", "pending", "pending"]


def test_should_derive_failed_when_no_results_and_idle():
    assert derive(expected_results=9, completed_results=0, work_pending=False) == "failed"


def test_should_derive_partial_when_some_results_and_idle():
    assert derive(expected_results=9, completed_results=3, work_pending=False) == "partial"


def test_should_derive_completed_when_all_slots_filled():
    assert derive(expected_results=9, completed_results=9, work_pending=False) == "completed"


def test_should_keep_running_while_work_pending():
    assert derive(expected_results=9, completed_results=9, work_pending=True) == "running"


def test_should_reject_pose_ids_and_pose_count_together():
    with pytest.raises(ValidationError):
        PhotoshootCreateRequest(
            staff_id=uuid.uuid4(),
            source_image_id=uuid.uuid4(),
            input_kind="flat_garment",
            model_ids=[uuid.uuid4()],
            pose_ids=["front"],
            pose_count=2,
            cloth_type="upper_body",
        )


async def _confirm_source(client, setup, service_client, secret, staff_id, **kind_overrides):
    body = _presign_body(staff_id, **kind_overrides)
    payload = JPEG if body["content_type"] == "image/jpeg" else PNG
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=body,
            headers=setup.headers(service_client, secret),
        )
    assert presign.status_code == 201, presign.text
    source_id = presign.json()["source_image_id"]
    with (
        patch(f"{STORAGE}.head_object", new_callable=AsyncMock) as head,
        patch(f"{STORAGE}.get_object_bytes", new_callable=AsyncMock) as get_bytes,
        patch(f"{STORAGE}.generate_download_url", new_callable=AsyncMock) as preview,
    ):
        head.return_value = {
            "content_type": body["content_type"],
            "content_length": len(payload),
        }
        get_bytes.return_value = payload
        preview.return_value = "https://minio.test/get"
        confirm = await client.post(
            f"/api/integration/v1/products/draft-1/source-images/{source_id}:confirm",
            json={"staff_id": staff_id},
            headers=setup.headers(service_client, secret),
        )
    assert confirm.status_code == 200, confirm.text
    return source_id


async def _setup_ready(
    client,
    monkeypatch,
    *,
    kind: str = "garment_on_model",
    poses: tuple[str, ...] = ("front", "side", "back"),
    n_models: int = 1,
    confirm: bool = True,
    product: str = "draft-1",
):
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-test-replicate")
    setup, service_client, secret, staff_id, link_id = await _bridge_product(
        client, product
    )
    owner = uuid.UUID(staff_id)
    models = [
        await _insert_model(owner, f"Model {index}", list(poses), service_client.tenant_id)
        for index in range(n_models)
    ]
    source_id = None
    if confirm:
        overrides = {"kind": kind}
        if kind == "flat_garment":
            overrides.update(
                content_type="image/png",
                size_bytes=len(PNG),
                filename="flat.png",
            )
        source_id = await _confirm_source(
            client, setup, service_client, secret, staff_id, **overrides
        )
    return SimpleNamespace(
        setup=setup,
        client=service_client,
        secret=secret,
        staff_id=staff_id,
        owner=owner,
        tenant_id=service_client.tenant_id,
        link_id=link_id,
        models=models,
        source_id=source_id,
        headers=setup.headers(service_client, secret),
        product=product,
    )


def _submit_body(ctx, **overrides):
    body = {
        "staff_id": ctx.staff_id,
        "source_image_id": ctx.source_id,
        "input_kind": "garment_on_model",
        "model_ids": [str(model.id) for model in ctx.models],
        "pose_ids": ["front", "side", "back"],
        "cloth_type": "upper_body",
    }
    body.update(overrides)
    return body


async def _post_photoshoot(client, ctx, body, **header_extra):
    headers = dict(ctx.headers)
    headers.update(header_extra)
    with patch(SEND_TASK) as send:
        response = await client.post(
            PHOTOSHOOTS.format(pid=ctx.product),
            json=body,
            headers=headers,
        )
    return response, send


@pytest.mark.asyncio
async def test_should_accept_photoshoot_and_freeze_expected_results(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, n_models=2)
    response, send = await _post_photoshoot(client, ctx, _submit_body(ctx))
    assert response.status_code == 202, response.text
    data = response.json()
    uuid.UUID(data["photoshoot_id"])
    assert data["status"] == "queued"
    assert data["expected_results"] == 6
    assert data["external_product_id"] == "draft-1"
    assert {row["name"]: row["status"] for row in data["stages"]} == {
        "tryoff": "pending",
        "vton": "pending",
        "poses": "pending",
        "composition": "skipped",
    }
    assert data["created_at"]
    _assert_no_secrets(data)
    send.assert_called_once()
    assert send.call_args.args[0] == "tasks.photoshoot_orchestration.photoshoot_tick_task"
    assert send.call_args.kwargs["args"] == [data["photoshoot_id"]]
    assert send.call_args.kwargs["queue"] == "photoshoot"

    async with database.async_session() as session:
        row = (
            await session.execute(
                select(Photoshoot).where(
                    Photoshoot.id == uuid.UUID(data["photoshoot_id"])
                )
            )
        ).scalar_one()
        assert row.expected_results == 6
        assert row.status == "queued"
        assert row.configuration["pose_types"] == ["front", "side", "back"]
        assert row.variant_key is None
        stages = (
            await session.execute(
                select(PhotoshootStage).where(
                    PhotoshootStage.photoshoot_id == row.id
                )
            )
        ).scalars().all()
        assert len(stages) == 4
        selections = (await session.execute(select(PublicationSelection))).scalars().all()
        assert selections == []


@pytest.mark.asyncio
async def test_should_skip_tryoff_for_flat_garment(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="flat_garment")
    response, _send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    assert response.status_code == 202, response.text
    stages = {row["name"]: row["status"] for row in response.json()["stages"]}
    assert stages["tryoff"] == "skipped"
    assert stages["tryoff"] != "failed"
    assert response.json()["expected_results"] == 1


@pytest.mark.asyncio
async def test_should_accept_empty_overlay_without_composition(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, _send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, overlay={"text": "   "}, pose_ids=["front"]),
    )
    assert response.status_code == 202, response.text
    stages = {row["name"]: row["status"] for row in response.json()["stages"]}
    assert stages["composition"] == "skipped"


@pytest.mark.asyncio
async def test_should_queue_composition_when_overlay_text_present(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, _send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, overlay={"text": "blusa-01"}, pose_ids=["front"]),
    )
    assert response.status_code == 202, response.text
    stages = {row["name"]: row["status"] for row in response.json()["stages"]}
    assert stages["composition"] == "pending"


@pytest.mark.asyncio
async def test_should_reject_source_not_ready(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, confirm=False)
    with patch(f"{STORAGE}.generate_upload_url", new_callable=AsyncMock) as sign:
        sign.return_value = "https://minio.test/put"
        presign = await client.post(
            "/api/integration/v1/products/draft-1/source-images:presign",
            json=_presign_body(ctx.staff_id),
            headers=ctx.headers,
        )
    ctx.source_id = presign.json()["source_image_id"]
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SOURCE_IMAGE_NOT_READY"
    send.assert_not_called()
    async with database.async_session() as session:
        assert (await session.execute(select(Photoshoot))).scalars().all() == []


@pytest.mark.asyncio
async def test_should_reject_kind_mismatch(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, kind="garment_on_model")
    response, send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, input_kind="flat_garment", pose_ids=["front"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SOURCE_IMAGE_KIND_MISMATCH"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_empty_model_ids(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, model_ids=[], pose_ids=["front"])
    )
    assert response.status_code == 422
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_unknown_cloth_type(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, cloth_type="overall", pose_ids=["front"])
    )
    assert response.status_code == 422
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_pose_count_out_of_range(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    for count in (0, 4):
        response, send = await _post_photoshoot(
            client,
            ctx,
            _submit_body(ctx, pose_ids=None, pose_count=count),
        )
        assert response.status_code == 422
        send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_foreign_model_before_enqueue(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    other = _BridgeSetup(client)
    foreign, _tenant = await other.register_staff(email="other-owner@test.com")
    alien = await _insert_model(foreign.id, "Alien", ["front"], foreign.tenant_id)
    response, send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, model_ids=[str(alien.id)], pose_ids=["front"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MODEL_NOT_AVAILABLE"
    send.assert_not_called()
    async with database.async_session() as session:
        assert (await session.execute(select(Photoshoot))).scalars().all() == []


@pytest.mark.asyncio
async def test_should_reject_model_missing_requested_pose(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch, poses=("front",))
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front", "side"])
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "POSE_SELECTION_INVALID"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_archived_template(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    template = await _insert_template(
        created_by=ctx.owner, name="Old look", status="archived"
    )
    response, send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, template_id=str(template.id), pose_ids=["front"]),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TEMPLATE_NOT_SELECTABLE"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_reject_overlay_text_over_max(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(
            ctx,
            overlay={"text": "x" * (SKU_MAX_LENGTH + 1)},
            pose_ids=["front"],
        ),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "OVERLAY_TEXT_TOO_LONG"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_accept_overlay_slug_longer_than_thirty(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    slug = "blusa-manga-globo-estampada-verano"
    assert 30 < len(slug) <= SKU_MAX_LENGTH
    response, send = await _post_photoshoot(
        client,
        ctx,
        _submit_body(ctx, overlay={"text": slug}, pose_ids=["front"]),
    )
    assert response.status_code == 202, response.text
    send.assert_called_once()


@pytest.mark.asyncio
async def test_should_persist_variant_key_without_filtering(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, variant_key="navy", pose_ids=["front"])
    )
    assert response.status_code == 202, response.text
    assert response.json()["variant_key"] == "navy"
    assert response.json()["created"] is True
    send.assert_called_once()
    async with database.async_session() as session:
        row = (
            await session.execute(
                select(Photoshoot).where(
                    Photoshoot.id == uuid.UUID(response.json()["photoshoot_id"])
                )
            )
        ).scalar_one()
        assert row.variant_key == "navy"


@pytest.mark.asyncio
async def test_should_forbid_revoked_staff(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    revoked = await client.post(
        "/api/integration/v1/staff-identities/42:revoke",
        headers=ctx.headers,
    )
    assert revoked.status_code == 200
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "STAFF_FORBIDDEN"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_return_404_when_product_link_missing(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    with patch(SEND_TASK) as send:
        response = await client.post(
            PHOTOSHOOTS.format(pid="missing"),
            json=_submit_body(ctx, pose_ids=["front"]),
            headers=ctx.headers,
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PRODUCT_LINK_NOT_FOUND"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_forbid_foreign_and_missing_source_the_same_way(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    created = await client.post(
        "/api/integration/v1/product-links",
        json={"external_product_id": "draft-2", "staff_id": ctx.staff_id},
        headers=ctx.headers,
    )
    assert created.status_code == 201, created.text

    with patch(SEND_TASK) as send:
        foreign = await client.post(
            PHOTOSHOOTS.format(pid="draft-2"),
            json=_submit_body(ctx, pose_ids=["front"]),
            headers=ctx.headers,
        )
        missing = await client.post(
            PHOTOSHOOTS.format(pid="draft-2"),
            json=_submit_body(
                ctx, source_image_id=str(uuid.uuid4()), pose_ids=["front"]
            ),
            headers=ctx.headers,
        )
    assert foreign.status_code == 403
    assert missing.status_code == 403
    assert foreign.json()["detail"] == missing.json()["detail"]
    assert foreign.json()["detail"]["code"] == "SOURCE_IMAGE_FORBIDDEN"
    send.assert_not_called()


@pytest.mark.asyncio
async def test_should_return_identical_401_without_service_headers(client):
    response = await client.post(
        PHOTOSHOOTS.format(pid="draft-1"),
        json={
            "staff_id": str(uuid.uuid4()),
            "source_image_id": str(uuid.uuid4()),
            "input_kind": "flat_garment",
            "model_ids": [str(uuid.uuid4())],
            "pose_ids": ["front"],
            "cloth_type": "upper_body",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] in {
        "Unauthorized",
        "Invalid service credentials",
    }


@pytest.mark.asyncio
async def test_should_return_503_when_replicate_credential_missing(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "")
    response, send = await _post_photoshoot(
        client, ctx, _submit_body(ctx, pose_ids=["front"])
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PROVIDER_CREDENTIAL_MISSING"
    send.assert_not_called()
    async with database.async_session() as session:
        assert (await session.execute(select(Photoshoot))).scalars().all() == []


@pytest.mark.asyncio
async def test_should_replay_same_idempotency_key_and_payload(client, monkeypatch):
    ctx = await _setup_ready(client, monkeypatch)
    body = _submit_body(ctx, pose_ids=["front"])
    first, send_first = await _post_photoshoot(
        client, ctx, body, **{"Idempotency-Key": "same-key"}
    )
    second, send_second = await _post_photoshoot(
        client, ctx, body, **{"Idempotency-Key": "same-key"}
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["photoshoot_id"] == second.json()["photoshoot_id"]
    assert second.json()["created"] is False
    send_first.assert_called_once()
    send_second.assert_not_called()
    async with database.async_session() as session:
        rows = (await session.execute(select(Photoshoot))).scalars().all()
    assert len(rows) == 1
