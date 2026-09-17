import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

import core.database as database
from models.generation_job import GenerationJob
from models.mayorista import Mayorista
from models.provider_invocation import ProviderInvocation
from services.idempotency_service import compute_payload_fingerprint
from services.image_generation_providers import (
    ProviderInvocationResult,
    ProviderNoResultError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
)
from services.retry_policy_service import RetryPolicyService
from services.usage_accounting_service import UsageAccountingService
from tasks.image_generation import _process_job
from tests.conftest import login_user, register_user


async def _promote_to_staff(email: str = "test@mayorista.com") -> None:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        user.role = "staff"
        await session.commit()


async def _owner_id(email: str = "test@mayorista.com") -> uuid.UUID:
    async with database.async_session() as session:
        user = (
            await session.execute(select(Mayorista).where(Mayorista.email == email.lower()))
        ).scalar_one()
        return user.id


async def _create_job(owner_id: uuid.UUID, **overrides) -> GenerationJob:
    defaults = dict(
        owner_id=owner_id,
        mode="text",
        provider="openai",
        status="queued",
        input_data={"mode": "text", "prompt": "a red jacket"},
    )
    defaults.update(overrides)
    async with database.async_session() as session:
        job = GenerationJob(**defaults)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def _reload_job(job_id: uuid.UUID) -> GenerationJob:
    async with database.async_session() as session:
        result = await session.execute(select(GenerationJob).where(GenerationJob.id == job_id))
        return result.scalar_one()


async def _list_invocations(job_id: uuid.UUID) -> list[ProviderInvocation]:
    async with database.async_session() as session:
        result = await session.execute(
            select(ProviderInvocation)
            .where(ProviderInvocation.job_id == job_id)
            .order_by(ProviderInvocation.attempt_number)
        )
        return list(result.scalars().all())


async def _setup_staff(client, email: str = "test@mayorista.com") -> uuid.UUID:
    await register_user(client, email=email)
    await login_user(client, email=email)
    await _promote_to_staff(email)
    return await _owner_id(email)


# ---------------------------------------------------------------------------
# RetryPolicyService (pure logic)
# ---------------------------------------------------------------------------


def test_classify_429_is_transient_and_retryable():
    policy = RetryPolicyService()
    classification = policy.classify_http_error(429)
    assert classification.category == "transient"
    assert classification.retryable is True
    assert classification.code == "PROVIDER_RATE_LIMITED"


def test_classify_other_http_error_is_terminal():
    policy = RetryPolicyService()
    classification = policy.classify_http_error(400)
    assert classification.category == "terminal"
    assert classification.retryable is False


def test_timeout_is_never_auto_retried():
    policy = RetryPolicyService()
    classification = policy.classify_timeout()
    decision = policy.decide(classification, attempt_number=1, retry_after_seconds=None)
    assert decision.should_retry is False


def test_transient_error_retries_up_to_two_times_honoring_retry_after():
    policy = RetryPolicyService()
    classification = policy.classify_http_error(429)

    first = policy.decide(classification, attempt_number=1, retry_after_seconds=12)
    assert first.should_retry is True
    assert first.delay_seconds == 12
    assert first.next_attempt_number == 2

    second = policy.decide(classification, attempt_number=2, retry_after_seconds=None)
    assert second.should_retry is True
    assert second.next_attempt_number == 3

    third = policy.decide(classification, attempt_number=3, retry_after_seconds=None)
    assert third.should_retry is False


def test_terminal_error_never_retries():
    policy = RetryPolicyService()
    classification = policy.classify_request_error()
    decision = policy.decide(classification, attempt_number=1, retry_after_seconds=None)
    assert decision.should_retry is False


# ---------------------------------------------------------------------------
# UsageAccountingService (pure logic)
# ---------------------------------------------------------------------------


def test_usage_reported_when_provider_returns_recognized_fields():
    service = UsageAccountingService()
    record = service.normalize("gpt-image-1", {"total_tokens": 120, "input_tokens": 40})
    assert record.status == "reported"
    assert record.model == "gpt-image-1"
    assert record.raw == {"total_tokens": 120, "input_tokens": 40}


def test_usage_unknown_when_provider_omits_usage():
    service = UsageAccountingService()
    record = service.normalize("gpt-image-1", None)
    assert record.status == "unknown"
    assert record.call_count is None


def test_usage_unknown_not_zero_when_fields_unrecognized():
    service = UsageAccountingService()
    record = service.normalize("gpt-image-1", {"unrecognized_field": 1})
    assert record.status == "unknown"
    assert record.call_count is None


# ---------------------------------------------------------------------------
# Idempotency (API-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_idempotency_key_and_payload_returns_one_job(client):
    await _setup_staff(client)
    payload = {"mode": "text", "prompt": "a red jacket"}

    with patch("api.routers.image_generation.celery_app.send_task") as mock_send:
        first = await client.post(
            "/api/image-generation/jobs",
            json=payload,
            headers={"Idempotency-Key": "key-1"},
        )
        second = await client.post(
            "/api/image-generation/jobs",
            json=payload,
            headers={"Idempotency-Key": "key-1"},
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_same_idempotency_key_different_payload_is_conflict(client):
    await _setup_staff(client)

    with patch("api.routers.image_generation.celery_app.send_task"):
        first = await client.post(
            "/api/image-generation/jobs",
            json={"mode": "text", "prompt": "a red jacket"},
            headers={"Idempotency-Key": "key-2"},
        )
        second = await client.post(
            "/api/image-generation/jobs",
            json={"mode": "text", "prompt": "a blue jacket"},
            headers={"Idempotency-Key": "key-2"},
        )

    assert first.status_code == 202
    assert second.status_code == 409


def test_payload_fingerprint_is_deterministic_regardless_of_key_order():
    a = compute_payload_fingerprint({"mode": "text", "prompt": "x"})
    b = compute_payload_fingerprint({"prompt": "x", "mode": "text"})
    assert a == b


# ---------------------------------------------------------------------------
# Worker orchestration: success, retry, timeout, terminal, duplicate delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_success_records_invocation_and_usage(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)

    fake_result = ProviderInvocationResult(
        image_bytes=b"fake-image-bytes",
        provider_model="gpt-image-1",
        usage={"total_tokens": 50},
    )
    with (
        patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls,
        patch("tasks.image_generation.StorageService") as mock_storage_cls,
    ):
        mock_provider_cls.return_value.generate = AsyncMock(return_value=fake_result)
        mock_storage_cls.return_value.upload_bytes = AsyncMock()

        retry_delay = await _process_job(job.id)

    assert retry_delay is None
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "completed"
    assert reloaded.usage_status == "reported"
    assert reloaded.usage_model == "gpt-image-1"
    assert reloaded.lock_token is None

    invocations = await _list_invocations(job.id)
    assert len(invocations) == 1
    assert invocations[0].status == "succeeded"
    assert invocations[0].usage_status == "reported"


@pytest.mark.asyncio
async def test_worker_rate_limit_schedules_retry_and_keeps_job_queued(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock(
            side_effect=ProviderRateLimitedError(retry_after_seconds=7)
        )
        retry_delay = await _process_job(job.id)

    assert retry_delay == 7
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "queued"
    assert reloaded.retry_count == 1
    assert reloaded.lock_token is None

    invocations = await _list_invocations(job.id)
    assert invocations[0].status == "failed"
    assert invocations[0].error_category == "transient"


@pytest.mark.asyncio
async def test_worker_timeout_does_not_auto_retry(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock(side_effect=ProviderTimeoutError())
        retry_delay = await _process_job(job.id)

    assert retry_delay is None
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "failed"
    assert reloaded.error_code == "PROVIDER_TIMEOUT"
    assert reloaded.usage_status == "unknown"

    invocations = await _list_invocations(job.id)
    assert invocations[0].status == "timed_out"
    assert invocations[0].error_category == "transient"


@pytest.mark.asyncio
async def test_worker_no_result_is_terminal(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock(side_effect=ProviderNoResultError())
        retry_delay = await _process_job(job.id)

    assert retry_delay is None
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "failed"
    assert reloaded.error_code == "PROVIDER_NO_RESULT"

    invocations = await _list_invocations(job.id)
    assert invocations[0].error_category == "terminal"


@pytest.mark.asyncio
async def test_worker_skips_job_that_is_not_queued(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id, status="completed")

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock()
        retry_delay = await _process_job(job.id)

    assert retry_delay is None
    mock_provider_cls.return_value.generate.assert_not_called()
    assert await _list_invocations(job.id) == []


@pytest.mark.asyncio
async def test_worker_skips_when_lease_already_held(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id, lock_token=uuid.uuid4())

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock()
        retry_delay = await _process_job(job.id)

    assert retry_delay is None
    mock_provider_cls.return_value.generate.assert_not_called()
    assert await _list_invocations(job.id) == []


# ---------------------------------------------------------------------------
# Invocation history visible via GET, usage summary correctness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_exposes_attempt_history_and_usage(client):
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)

    fake_result = ProviderInvocationResult(
        image_bytes=b"bytes", provider_model="gpt-image-1", usage=None
    )
    with (
        patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls,
        patch("tasks.image_generation.StorageService") as mock_storage_cls,
    ):
        mock_provider_cls.return_value.generate = AsyncMock(return_value=fake_result)
        mock_storage_cls.return_value.upload_bytes = AsyncMock()
        await _process_job(job.id)

    response = await client.get(f"/api/image-generation/jobs/{job.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["status"] == "succeeded"
    assert body["usage"] == {"status": "unknown", "model": "gpt-image-1", "call_count": None}


# ---------------------------------------------------------------------------
# Manual retry endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_retry_allowed_after_timeout(client):
    await _setup_staff(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock(side_effect=ProviderTimeoutError())
        await _process_job(job.id)

    with patch("api.routers.image_generation.celery_app.send_task") as mock_send:
        response = await client.post(f"/api/image-generation/jobs/{job.id}/retry")

    assert response.status_code == 202
    mock_send.assert_called_once_with("tasks.generate_image", args=[str(job.id)])
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "queued"


@pytest.mark.asyncio
async def test_manual_retry_rejected_for_terminal_error(client):
    await _setup_staff(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)

    with patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls:
        mock_provider_cls.return_value.generate = AsyncMock(side_effect=ProviderNoResultError())
        await _process_job(job.id)

    with patch("api.routers.image_generation.celery_app.send_task") as mock_send:
        response = await client.post(f"/api/image-generation/jobs/{job.id}/retry")

    assert response.status_code == 409
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_manual_retry_rejected_when_job_never_attempted(client):
    await _setup_staff(client)
    owner_id = await _owner_id()
    job = await _create_job(owner_id)

    response = await client.post(f"/api/image-generation/jobs/{job.id}/retry")
    assert response.status_code == 409
