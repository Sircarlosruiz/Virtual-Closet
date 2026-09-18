"""Contract tests for the authenticated Virtual Closet <-> BFashion bridge.

Covers accepted requests, fail-closed rejections, owner/tenant scoping and
idempotent replay for bolt 047.
"""

import json
import secrets
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

import core.database as database
from core.config import settings
from core.security import hash_password
from models.generation_job import GenerationJob
from models.mayorista import Mayorista
from models.product_link import ProductLink
from models.service_client import ServiceClient
from tests.conftest import register_user

SEND_TASK_PATH = "api.routers.integration.celery_app.send_task"


class _BridgeSetup:
    """Test helper to seed a tenant, service client and product link."""

    def __init__(self, client) -> None:
        self.client = client

    async def register_staff(self, email: str = "staff@test.com", role: str = "staff"):
        await register_user(self.client, email=email)
        async with database.async_session() as session:
            user = (
                await session.execute(select(Mayorista).where(Mayorista.email == email))
            ).scalar_one()
            user.role = role
            await session.commit()
            await session.refresh(user)
            return user, user.tenant_id

    async def create_service_client(
        self, tenant_id: uuid.UUID, system: str = "bfashion", active: bool = True
    ) -> tuple[ServiceClient, str]:
        raw_secret = secrets.token_urlsafe(32)
        async with database.async_session() as session:
            service_client = ServiceClient(
                name=f"svc-{uuid.uuid4().hex[:8]}",
                system=system,
                secret_hash=hash_password(raw_secret),
                tenant_id=tenant_id,
                is_active=active,
            )
            session.add(service_client)
            await session.commit()
            await session.refresh(service_client)
            return service_client, raw_secret

    async def create_product_link(
        self,
        tenant_id: uuid.UUID,
        mayorista_id: uuid.UUID,
        system: str = "bfashion",
        external_product_id: str = "prod-1",
        external_wholesaler_id: str | None = None,
        active: bool = True,
    ) -> ProductLink:
        async with database.async_session() as session:
            link = ProductLink(
                system=system,
                external_product_id=external_product_id,
                external_wholesaler_id=external_wholesaler_id,
                mayorista_id=mayorista_id,
                tenant_id=tenant_id,
                is_active=active,
            )
            session.add(link)
            await session.commit()
            await session.refresh(link)
            return link

    @staticmethod
    def headers(service_client: ServiceClient, secret: str) -> dict[str, str]:
        return {
            "X-Service-Id": str(service_client.id),
            "X-Service-Secret": secret,
        }


def _body(staff_id, **overrides) -> dict:
    body = {
        "staff_id": str(staff_id),
        "external_product_id": "prod-1",
        "generation": {"mode": "text", "prompt": "a red jacket"},
    }
    body.update(overrides)
    return body


def _assert_no_secrets(payload: dict) -> None:
    serialized = json.dumps(payload).lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized


@pytest.mark.asyncio
async def test_bridge_creates_job_for_valid_link(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)

    with patch(SEND_TASK_PATH) as mock_send:
        response = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=setup.headers(service_client, secret),
        )

    assert response.status_code == 202, response.text
    data = response.json()
    assert data["status"] == "queued"
    assert data["mode"] == "text"
    assert data["provider"] == "openai"
    assert data["external_product_id"] == "prod-1"
    _assert_no_secrets(data)
    mock_send.assert_called_once_with("tasks.generate_image", args=[data["job_id"]])

    async with database.async_session() as session:
        job = (
            await session.execute(
                select(GenerationJob).where(GenerationJob.id == uuid.UUID(data["job_id"]))
            )
        ).scalar_one()
        assert job.owner_id == staff.id
        assert "api_key" not in json.dumps(job.input_data).lower()
        if settings.OPENAI_API_KEY.strip():
            assert settings.OPENAI_API_KEY not in json.dumps(job.input_data)


@pytest.mark.asyncio
async def test_bridge_rejects_unknown_product_link(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)

    with patch(SEND_TASK_PATH) as mock_send:
        response = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=setup.headers(service_client, secret),
        )

    assert response.status_code == 404
    mock_send.assert_not_called()
    async with database.async_session() as session:
        jobs = (await session.execute(select(GenerationJob))).scalars().all()
        assert jobs == []


@pytest.mark.asyncio
async def test_bridge_rejects_inactive_link(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id, active=False)

    response = await client.post(
        "/api/integration/v1/products/generation-jobs",
        json=_body(staff.id),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bridge_rejects_mismatched_wholesaler(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(
        tenant_id, staff.id, external_wholesaler_id="wholesaler-A"
    )

    response = await client.post(
        "/api/integration/v1/products/generation-jobs",
        json=_body(staff.id, external_wholesaler_id="wholesaler-B"),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bridge_rejects_non_staff_actor(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff(role="mayorista")
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)

    response = await client.post(
        "/api/integration/v1/products/generation-jobs",
        json=_body(staff.id),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bridge_rejects_cross_tenant_link(client):
    setup = _BridgeSetup(client)
    staff_a, tenant_a = await setup.register_staff(email="staff-a@test.com")
    staff_b, tenant_b = await setup.register_staff(email="staff-b@test.com")
    service_client, secret = await setup.create_service_client(tenant_a)
    # Link belongs to tenant B while the service client is scoped to tenant A.
    await setup.create_product_link(tenant_b, staff_b.id)

    response = await client.post(
        "/api/integration/v1/products/generation-jobs",
        json=_body(staff_b.id),
        headers=setup.headers(service_client, secret),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bridge_rejects_invalid_service_credentials(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, _ = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)

    response = await client.post(
        "/api/integration/v1/products/generation-jobs",
        json=_body(staff.id),
        headers=setup.headers(service_client, "wrong-secret"),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bridge_status_retrievable_by_link_owner(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)

    with patch(SEND_TASK_PATH):
        created = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=setup.headers(service_client, secret),
        )
    job_id = created.json()["job_id"]

    status_response = await client.get(
        f"/api/integration/v1/products/prod-1/generation-jobs/{job_id}",
        headers=setup.headers(service_client, secret),
    )
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["job_id"] == job_id
    assert status_response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_bridge_status_rejects_job_owned_by_another_tenant(client):
    setup = _BridgeSetup(client)
    staff_a, tenant_a = await setup.register_staff(email="staff-a@test.com")
    staff_b, tenant_b = await setup.register_staff(email="staff-b@test.com")
    service_client_a, secret_a = await setup.create_service_client(tenant_a)
    service_client_b, secret_b = await setup.create_service_client(tenant_b)
    await setup.create_product_link(tenant_a, staff_a.id, external_product_id="prod-A")
    await setup.create_product_link(tenant_b, staff_b.id, external_product_id="prod-B")

    with patch(SEND_TASK_PATH):
        created = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff_a.id, external_product_id="prod-A"),
            headers=setup.headers(service_client_a, secret_a),
        )
    job_id = created.json()["job_id"]

    # Tenant B cannot read tenant A's job through its own link.
    response = await client.get(
        f"/api/integration/v1/products/prod-B/generation-jobs/{job_id}",
        headers=setup.headers(service_client_b, secret_b),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bridge_idempotent_replay_returns_same_job(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)
    headers = {**setup.headers(service_client, secret), "Idempotency-Key": "bridge-1"}

    with patch(SEND_TASK_PATH) as mock_send:
        first = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=headers,
        )
        second = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=headers,
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_bridge_idempotency_conflict_on_changed_payload(client):
    setup = _BridgeSetup(client)
    staff, tenant_id = await setup.register_staff()
    service_client, secret = await setup.create_service_client(tenant_id)
    await setup.create_product_link(tenant_id, staff.id)
    headers = {**setup.headers(service_client, secret), "Idempotency-Key": "bridge-2"}

    with patch(SEND_TASK_PATH):
        first = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id),
            headers=headers,
        )
        second = await client.post(
            "/api/integration/v1/products/generation-jobs",
            json=_body(staff.id, generation={"mode": "text", "prompt": "a blue jacket"}),
            headers=headers,
        )

    assert first.status_code == 202
    assert second.status_code == 409
