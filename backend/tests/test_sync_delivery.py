"""Sync delivery: per-destination status, idempotent retry, no regeneration."""

import pytest
from sqlalchemy import func, select

import core.database as database
from models.generation_job import GenerationJob
from models.publication import ProductImage, SyncDelivery
from tests.conftest import login_user
from tests.publication_helpers import create_completed_job
from tests.test_integration_bridge import _BridgeSetup


@pytest.mark.asyncio
async def test_should_sync_both_destinations_when_delivery_succeeds(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)

    response = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
    )
    assert response.status_code == 201, response.text
    by_dest = {row["destination"]: row for row in response.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "synced"
    assert by_dest["bfashion"]["external_ref"]
    assert fake_bfashion.calls[0].durable_object_key == "generated/base.png"
    assert fake_bfashion.calls[0].configuration["generation_job_id"] == str(job.id)

    async with database.async_session() as session:
        image = (await session.execute(select(ProductImage))).scalar_one()
        assert image.configuration["mode"] == "text"
        assert image.minio_key == "generated/base.png"


@pytest.mark.asyncio
async def test_should_isolate_failed_destination_and_retry_without_duplicates(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)
    fake_bfashion.fail = True

    first = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
    )
    assert first.status_code == 201, first.text
    by_dest = {row["destination"]: row for row in first.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "failed"
    assert by_dest["bfashion"]["retryable"] is True
    publication_id = first.json()["id"]

    async with database.async_session() as session:
        jobs_before = (
            await session.execute(select(func.count(GenerationJob.id)))
        ).scalar_one()
        images_before = (
            await session.execute(select(func.count(ProductImage.id)))
        ).scalar_one()
        assert images_before == 1

    fake_bfashion.fail = False
    retried = await client.post(
        f"/api/publications/{publication_id}/retry",
        params={"product_link_id": str(link.id)},
    )
    assert retried.status_code == 200, retried.text
    by_dest = {row["destination"]: row for row in retried.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "synced"

    duplicate = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == publication_id

    async with database.async_session() as session:
        jobs_after = (
            await session.execute(select(func.count(GenerationJob.id)))
        ).scalar_one()
        images_after = (
            await session.execute(select(func.count(ProductImage.id)))
        ).scalar_one()
        assert jobs_after == jobs_before
        assert images_after == 1
        deliveries = (await session.execute(select(SyncDelivery))).scalars().all()
        assert len(deliveries) == 2
    assert len(fake_bfashion.calls) == 2


@pytest.mark.asyncio
async def test_should_not_mark_other_destination_when_bfashion_fails_permanently(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    await login_user(client, email="staff@test.com")
    link = await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)
    fake_bfashion.fail = True
    fake_bfashion.retryable = False

    response = await client.post(
        "/api/publications",
        json={
            "product_link_id": str(link.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
    )
    assert response.status_code == 201
    by_dest = {row["destination"]: row for row in response.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "failed"
    assert by_dest["bfashion"]["retryable"] is False


@pytest.mark.asyncio
async def test_s2s_publication_uses_product_link_and_staff_assertion(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id)

    response = await client.post(
        "/api/integration/v1/products/prod-1/publications",
        json={
            "staff_id": str(staff.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 201, response.text
    by_dest = {row["destination"]: row for row in response.json()["deliveries"]}
    assert by_dest["virtual_closet"]["status"] == "synced"
    assert by_dest["bfashion"]["status"] == "synced"

    missing = await client.post(
        "/api/integration/v1/products/unknown/publications",
        json={
            "staff_id": str(staff.id),
            "generation_job_id": str(job.id),
            "decision": "selected",
        },
        headers=setup.headers(service_client, secret),
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_preview_url_is_derived_from_durable_key(
    client, fake_bfashion, preview_urls
):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)
    job = await create_completed_job(staff.id, "generated/preview-me.png")

    status = await client.get(
        f"/api/integration/v1/products/prod-1/generation-jobs/{job.id}",
        headers=setup.headers(service_client, secret),
    )
    assert status.status_code == 200, status.text
    assert (
        status.json()["preview_url"] == "https://preview.test/generated/preview-me.png"
    )

    candidates = await client.get(
        f"/api/integration/v1/products/prod-1/generation-jobs/{job.id}/publication-candidates",
        headers=setup.headers(service_client, secret),
    )
    assert candidates.status_code == 200
    raw = candidates.json()[0]
    assert raw["durable_object_key"] == "generated/preview-me.png"
    assert raw["preview_url"] == "https://preview.test/generated/preview-me.png"
