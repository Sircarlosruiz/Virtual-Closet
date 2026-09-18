"""Publication selection: explicit staff decisions, no auto-publish."""

import uuid

import pytest
from sqlalchemy import func, select

import core.database as database
from models.generation_job import GenerationJob
from models.mayorista import Mayorista
from models.product_overlay import CompositionVersion, ProductOverlay
from models.publication import ProductImage, PublicationSelection, SyncDelivery
from tests.conftest import login_user, register_user
from tests.publication_helpers import create_completed_job
from tests.test_integration_bridge import _BridgeSetup


async def _promote_to_staff(email: str) -> Mayorista:
    async with database.async_session() as session:
        user = (
            await session.execute(
                select(Mayorista).where(Mayorista.email == email.lower())
            )
        ).scalar_one()
        user.role = "staff"
        await session.commit()
        await session.refresh(user)
        return user


async def _create_composition_version(
    job: GenerationJob,
    created_by: uuid.UUID,
    *,
    version: int = 1,
    status: str = "valid",
    rendered_key: str | None = "compositions/v1.png",
    spec_hash: str = "a" * 64,
) -> CompositionVersion:
    async with database.async_session() as session:
        overlay = (
            await session.execute(
                select(ProductOverlay).where(ProductOverlay.generation_job_id == job.id)
            )
        ).scalar_one_or_none()
        if overlay is None:
            overlay = ProductOverlay(
                generation_job_id=job.id,
                base_image_key=job.result_key,
                created_by=created_by,
            )
            session.add(overlay)
            await session.flush()
        row = CompositionVersion(
            overlay_id=overlay.id,
            version=version,
            sku_normalized=f"REF: CAM-{version:03d}",
            placement={"anchor": "bottom-right", "offset_x": 24, "offset_y": 24},
            style={"color": "#000000", "font_size": 48},
            spec_hash=spec_hash,
            font_version="default",
            status=status,
            rendered_key=rendered_key,
            fit_result={
                "fits": status == "valid",
                "rendered_width": 10,
                "rendered_height": 10,
                "available_width": 100,
                "available_height": 100,
                "reason": None if status == "valid" else "too wide",
            },
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


@pytest.mark.asyncio
async def test_should_select_only_chosen_candidates_when_others_discarded(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    selected_job = await create_completed_job(staff.id, "generated/sel.png")
    discarded_job = await create_completed_job(staff.id, "generated/disc.png")

    selected = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(selected_job.id),
            "decision": "selected",
        },
    )
    discarded = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(discarded_job.id),
            "decision": "discarded",
        },
    )

    assert selected.status_code == 201, selected.text
    assert discarded.status_code == 201, discarded.text
    assert {d["destination"] for d in selected.json()["deliveries"]} == {
        "virtual_closet",
        "bfashion",
    }
    assert discarded.json()["deliveries"] == []
    assert discarded.json()["decision"] == "discarded"

    async with database.async_session() as session:
        images = (await session.execute(select(ProductImage))).scalars().all()
        assert len(images) == 1
        assert images[0].generation_job_id == selected_job.id
        deliveries = (await session.execute(select(SyncDelivery))).scalars().all()
        assert all(
            row.publication_selection_id == uuid.UUID(selected.json()["id"])
            for row in deliveries
        )


@pytest.mark.asyncio
async def test_should_append_gallery_image_when_publishing_another_candidate(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    first = await create_completed_job(staff.id, "generated/one.png")
    second = await create_completed_job(staff.id, "generated/two.png")

    r1 = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(first.id),
            "decision": "selected",
        },
    )
    r2 = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(second.id),
            "decision": "selected",
        },
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]

    async with database.async_session() as session:
        images = (
            (
                await session.execute(
                    select(ProductImage).order_by(ProductImage.position)
                )
            )
            .scalars()
            .all()
        )
        assert [img.generation_job_id for img in images] == [first.id, second.id]
        assert images[0].minio_key == "generated/one.png"
        assert images[1].minio_key == "generated/two.png"


@pytest.mark.asyncio
async def test_should_require_new_selection_when_composition_version_changes(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)
    v1 = await _create_composition_version(job, staff.id, version=1, spec_hash="b" * 64)
    published = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "composition_version_id": str(v1.id),
            "decision": "selected",
        },
    )
    assert published.status_code == 201, published.text

    v2 = await _create_composition_version(
        job,
        staff.id,
        version=2,
        rendered_key="compositions/v2.png",
        spec_hash="c" * 64,
    )
    candidates = await client.get(
        f"/api/generation-jobs/{job.id}/publication-candidates",
        params={"product_link_id": str(link.id)},
    )
    assert candidates.status_code == 200, candidates.text
    by_version = {item["composition_version_id"]: item for item in candidates.json()}
    assert by_version[str(v1.id)]["decision"] == "selected"
    assert by_version[str(v2.id)]["decision"] is None
    assert by_version[str(v2.id)]["eligible"] is True

    async with database.async_session() as session:
        count = (
            await session.execute(select(func.count(ProductImage.id)))
        ).scalar_one()
        assert count == 1


@pytest.mark.asyncio
async def test_should_keep_discarded_historical_and_block_retry(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)
    created = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "decision": "discarded",
        },
    )
    assert created.status_code == 201
    publication_id = created.json()["id"]

    listed = await client.get(
        f"/api/generation-jobs/{job.id}/publication-candidates",
        params={"product_link_id": str(link.id)},
    )
    raw = next(item for item in listed.json() if item["kind"] == "generation_result")
    assert raw["decision"] == "discarded"
    assert raw["publication_id"] == publication_id

    retry = await client.post(
        f"/api/publications/{publication_id}/retry",
        params={"product_link_id": str(link.id)},
    )
    assert retry.status_code == 409


@pytest.mark.asyncio
async def test_should_fail_closed_when_product_link_unknown(
    client, fake_bfashion, preview_urls
):
    await register_user(client, email="staff@test.com")
    staff = await _promote_to_staff("staff@test.com")
    await login_user(client, email="staff@test.com")
    job = await create_completed_job(staff.id)

    response = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(uuid.uuid4()),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
    )
    assert response.status_code == 404
    async with database.async_session() as session:
        assert (
            await session.execute(select(func.count(PublicationSelection.id)))
        ).scalar_one() == 0
        assert (
            await session.execute(select(func.count(ProductImage.id)))
        ).scalar_one() == 0


@pytest.mark.asyncio
async def test_should_reject_incomplete_job_and_blocked_version(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)

    async with database.async_session() as session:
        queued = GenerationJob(
            owner_id=staff.id,
            mode="text",
            provider="openai",
            status="queued",
            input_data={"mode": "text", "prompt": "later"},
        )
        session.add(queued)
        await session.commit()
        await session.refresh(queued)

    incomplete = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(queued.id),
            "decision": "selected",
        },
    )
    assert incomplete.status_code == 409

    job = await create_completed_job(staff.id)
    blocked = await _create_composition_version(
        job,
        staff.id,
        status="blocked",
        rendered_key=None,
        spec_hash="d" * 64,
    )
    blocked_resp = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "composition_version_id": str(blocked.id),
            "decision": "selected",
        },
    )
    assert blocked_resp.status_code == 409


@pytest.mark.asyncio
async def test_should_forbid_non_staff_publication(client, fake_bfashion, preview_urls):
    await register_user(client, email="owner@test.com")
    await login_user(client, email="owner@test.com")
    response = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(uuid.uuid4()),
            "generation_job_id": str(uuid.uuid4()),
            "decision": "selected",
        },
    )
    assert response.status_code == 403
