import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from core.config import settings
from services.credential_gate_service import CredentialGateService, CredentialMissingError
from services.global_concurrency_service import GlobalConcurrencyService, RedisUnavailableError
from services.image_generation.replicate_tryon_adapter import ReplicateTryOnAdapter
from services.image_generation_providers import (
    ProviderInvocationResult,
    ProviderRequestError,
    ProviderTimeoutError,
)
from services.provider_timeout_policy import ProviderTimeoutPolicy
from services.retry_policy_service import RetryPolicyService
from tasks.image_generation import _get_provider, _process_job
from tests.test_image_generation_reliability import (
    _AlwaysAvailableSlot,
    _create_job,
    _list_invocations,
    _reload_job,
    _setup_staff,
)


@pytest.fixture(autouse=True)
def _default_worker_pool(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-test-replicate")
    monkeypatch.setattr(
        "tasks.image_generation._global_concurrency_service",
        lambda: _AlwaysAvailableSlot(),
    )


class _MemoryRedis:
    def __init__(self) -> None:
        self._sets: dict[str, set[str]] = {}
        self._strings: dict[str, str] = {}

    async def eval(self, script, numkeys, *keys_and_args):
        set_key, ttl_key, job_id, cap, _ttl = keys_and_args
        members = set(self._sets.get(set_key, set()))
        for member in list(members):
            if f"imggen:slot:{member}" not in self._strings:
                members.discard(member)
        self._sets[set_key] = members
        if job_id in members:
            self._strings[ttl_key] = "1"
            return 1
        if len(members) < int(cap):
            members.add(job_id)
            self._sets[set_key] = members
            self._strings[ttl_key] = "1"
            return 1
        return 0

    async def srem(self, key, member):
        self._sets.setdefault(key, set()).discard(member)

    async def delete(self, key):
        self._strings.pop(key, None)

    async def scard(self, key):
        return len(self._sets.get(key, set()))


class _CappedPool:
    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.held: set[str] = set()
        self.max_in_flight = 0

    async def try_acquire(self, job_id) -> bool:
        key = str(job_id)
        if key in self.held:
            return True
        if len(self.held) >= self.cap:
            return False
        self.held.add(key)
        self.max_in_flight = max(self.max_in_flight, len(self.held))
        return True

    async def release(self, job_id) -> None:
        self.held.discard(str(job_id))


def test_get_provider_wires_replicate_and_openai(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-openai")
    openai = _get_provider("openai")
    replicate = _get_provider("replicate")
    assert openai.__class__.__name__ == "OpenAIImageProvider"
    assert isinstance(replicate, ReplicateTryOnAdapter)


def test_get_provider_rejects_unknown() -> None:
    with pytest.raises(ProviderRequestError, match="not yet wired"):
        _get_provider("unknown-vendor")


def test_timeout_policy_is_independent_per_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "IMAGE_GENERATION_OPENAI_TIMEOUT_SECONDS", 60)
    monkeypatch.setattr(settings, "IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS", 900)
    policy = ProviderTimeoutPolicy()
    assert policy.timeout_for("openai").seconds == 60
    assert policy.timeout_for("replicate").seconds >= 900
    monkeypatch.setattr(settings, "IMAGE_GENERATION_OPENAI_TIMEOUT_SECONDS", 15)
    assert ProviderTimeoutPolicy().timeout_for("replicate").seconds == 900
    assert ProviderTimeoutPolicy().timeout_for("openai").seconds == 15


def test_credential_gate_checks_only_job_provider(monkeypatch) -> None:
    gate = CredentialGateService()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-present")
    gate.require("replicate")
    with pytest.raises(CredentialMissingError) as openai_exc:
        gate.require("openai")
    assert openai_exc.value.error_code == "PROVIDER_CREDENTIAL_MISSING"
    assert "r8-present" not in str(openai_exc.value)

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-present")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "")
    gate.require("openai")
    with pytest.raises(CredentialMissingError) as replicate_exc:
        gate.require("replicate")
    assert "sk-present" not in str(replicate_exc.value)


def test_credential_missing_is_not_retryable() -> None:
    decision = RetryPolicyService().decide(
        RetryPolicyService().classify_credential_missing(),
        attempt_number=1,
        retry_after_seconds=None,
    )
    assert decision.should_retry is False


@pytest.mark.asyncio
async def test_replicate_adapter_reuses_inner_provider_and_rejects_missing_keys() -> None:
    inner = MagicMock()
    inner.generate = AsyncMock(return_value=b"image-bytes")
    adapter = ReplicateTryOnAdapter(inner=inner, timeout_seconds=900)
    with pytest.raises(ProviderRequestError, match="garment"):
        await adapter.generate({"cloth_type": "upper_body"})

    result = await adapter.generate(
        {
            "cloth_type": "upper_body",
            "garment_bytes": b"garment",
            "model_bytes": b"model",
        }
    )
    inner.generate.assert_awaited_once_with(b"garment", b"model", "upper")
    assert result.image_bytes == b"image-bytes"


@pytest.mark.asyncio
async def test_replicate_adapter_times_out_as_provider_timeout() -> None:
    inner = MagicMock()

    async def _hang(*_args, **_kwargs):
        await asyncio.sleep(60)

    inner.generate = _hang
    adapter = ReplicateTryOnAdapter(inner=inner, timeout_seconds=0.01)
    with pytest.raises(ProviderTimeoutError):
        await adapter.generate(
            {"cloth_type": "upper", "garment_bytes": b"g", "model_bytes": b"m"}
        )


@pytest.mark.asyncio
async def test_memory_redis_cap_never_exceeds_limit() -> None:
    redis = _MemoryRedis()
    service = GlobalConcurrencyService(redis=redis, cap=2, ttl_seconds=30)
    first = uuid4()
    second = uuid4()
    third = uuid4()
    assert await service.try_acquire(first) is True
    assert await service.try_acquire(second) is True
    assert await service.try_acquire(third) is False
    assert await service.in_flight_count() == 2
    await service.release(first)
    assert await service.try_acquire(third) is True
    assert await service.in_flight_count() == 2


@pytest.mark.asyncio
async def test_global_concurrency_fail_closed_without_redis() -> None:
    service = GlobalConcurrencyService(redis=None)
    with pytest.raises(RedisUnavailableError):
        await service.try_acquire(uuid4())


@pytest.mark.asyncio
async def test_worker_replicate_job_completes_without_openai_key(client, monkeypatch) -> None:
    from unittest.mock import patch

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-present")
    owner_id = await _setup_staff(client)
    job = await _create_job(
        owner_id,
        mode="try_on",
        provider="replicate",
        input_data={
            "mode": "try_on",
            "cloth_type": "upper",
            "garment_bytes": "Zg==",
            "model_bytes": "bQ==",
        },
    )
    fake = ProviderInvocationResult(image_bytes=b"out", provider_model="catvton", usage=None)
    with (
        patch("tasks.image_generation._get_provider", return_value=MagicMock(generate=AsyncMock(return_value=fake))),
        patch("tasks.image_generation.StorageService") as storage_cls,
    ):
        storage_cls.return_value.upload_bytes = AsyncMock()
        result = await _process_job(job.id)

    assert result.reschedule_slot_wait is False
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "completed"
    assert reloaded.error_code is None


@pytest.mark.asyncio
async def test_worker_replicate_job_records_reported_usage_from_sidecar(client, monkeypatch):
    from unittest.mock import patch

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-present")
    owner_id = await _setup_staff(client)
    job = await _create_job(
        owner_id,
        mode="try_on",
        provider="replicate",
        input_data={
            "mode": "try_on",
            "cloth_type": "upper",
            "garment_bytes": "Zg==",
            "model_bytes": "bQ==",
        },
    )
    fake = ProviderInvocationResult(
        image_bytes=b"out",
        provider_model="zhengchong/catvton",
        usage={"prediction_id": "pred-live", "predict_time": 11.4},
    )
    with (
        patch(
            "tasks.image_generation._get_provider",
            return_value=MagicMock(generate=AsyncMock(return_value=fake), last_usage=fake.usage),
        ),
        patch("tasks.image_generation.StorageService") as storage_cls,
    ):
        storage_cls.return_value.upload_bytes = AsyncMock()
        result = await _process_job(job.id)

    assert result.reschedule_slot_wait is False
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "completed"
    assert reloaded.usage_status == "reported"
    assert reloaded.usage_model == "zhengchong/catvton"
    invocations = await _list_invocations(job.id)
    assert len(invocations) == 1
    assert invocations[0].usage_status == "reported"
    assert invocations[0].usage_model == "zhengchong/catvton"
    assert invocations[0].usage_raw == {"prediction_id": "pred-live", "predict_time": 11.4}
    assert invocations[0].usage_raw.get("total_tokens") is None


@pytest.mark.asyncio
async def test_worker_openai_job_fails_without_openai_key(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "r8-present")
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)
    result = await _process_job(job.id)
    assert result.retry_delay is None
    reloaded = await _reload_job(job.id)
    assert reloaded.status == "failed"
    assert reloaded.error_code == "PROVIDER_CREDENTIAL_MISSING"
    assert await _list_invocations(job.id) == []
    assert reloaded.lock_token is None


@pytest.mark.asyncio
async def test_worker_replicate_job_fails_without_replicate_key(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-present")
    monkeypatch.setattr(settings, "REPLICATE_API_KEY", "")
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id, provider="replicate", mode="try_on")
    result = await _process_job(job.id)
    reloaded = await _reload_job(job.id)
    assert result.retry_delay is None
    assert reloaded.status == "failed"
    assert reloaded.error_code == "PROVIDER_CREDENTIAL_MISSING"


@pytest.mark.asyncio
async def test_worker_reschedules_when_global_slot_denied(client, monkeypatch) -> None:
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)
    pool = _CappedPool(cap=0)

    async def _deny(_job_id):
        return False

    pool.try_acquire = _deny  # type: ignore[method-assign]
    monkeypatch.setattr("tasks.image_generation._global_concurrency_service", lambda: pool)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-present")
    result = await _process_job(job.id)
    reloaded = await _reload_job(job.id)
    assert result.reschedule_slot_wait is True
    assert reloaded.status == "queued"
    assert reloaded.concurrency_wait_started_at is not None
    assert reloaded.lock_token is None
    assert await _list_invocations(job.id) == []


@pytest.mark.asyncio
async def test_worker_cap_two_never_exceeds_in_flight(client, monkeypatch) -> None:
    owner_id = await _setup_staff(client)
    pool = _CappedPool(cap=2)
    current = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def _generate(_inputs):
        nonlocal current, max_seen
        async with lock:
            current += 1
            max_seen = max(max_seen, current)
        await asyncio.sleep(0.05)
        async with lock:
            current -= 1
        return ProviderInvocationResult(image_bytes=b"x", provider_model="m", usage=None)

    monkeypatch.setattr("tasks.image_generation._global_concurrency_service", lambda: pool)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-present")
    jobs = [await _create_job(owner_id) for _ in range(12)]
    provider = MagicMock(generate=_generate)

    from unittest.mock import patch

    with (
        patch("tasks.image_generation._get_provider", return_value=provider),
        patch("tasks.image_generation.StorageService") as storage_cls,
    ):
        storage_cls.return_value.upload_bytes = AsyncMock()
        pending = list(jobs)
        while pending:
            results = await asyncio.gather(*[_process_job(job.id) for job in pending])
            still = []
            for job, result in zip(pending, results, strict=True):
                if result.reschedule_slot_wait:
                    still.append(job)
            pending = still

    assert pool.max_in_flight <= 2
    assert max_seen <= 2
    for job in jobs:
        reloaded = await _reload_job(job.id)
        assert reloaded.status == "completed"


@pytest.mark.asyncio
async def test_get_job_exposes_queue_and_execution_durations(client, monkeypatch) -> None:
    owner_id = await _setup_staff(client)
    job = await _create_job(owner_id)
    fake = ProviderInvocationResult(image_bytes=b"x", provider_model="gpt-image-1", usage=None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-present")
    from unittest.mock import patch

    with (
        patch("tasks.image_generation.OpenAIImageProvider") as mock_provider_cls,
        patch("tasks.image_generation.StorageService") as mock_storage_cls,
    ):
        mock_provider_cls.return_value.generate = AsyncMock(return_value=fake)
        mock_storage_cls.return_value.upload_bytes = AsyncMock()
        await _process_job(job.id)

    response = await client.get(f"/api/image-generation/jobs/{job.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["queue_wait_seconds"] is not None
    assert body["execution_seconds"] is not None


def test_slot_wait_exhausted_uses_started_at(monkeypatch) -> None:
    from tasks.image_generation import _slot_wait_exhausted

    job = MagicMock()
    job.concurrency_wait_started_at = datetime.now(timezone.utc) - timedelta(hours=7)
    monkeypatch.setattr(settings, "IMAGE_GENERATION_SLOT_WAIT_MAX_SECONDS", 21600)
    assert _slot_wait_exhausted(job) is True
    job.concurrency_wait_started_at = datetime.now(timezone.utc)
    assert _slot_wait_exhausted(job) is False
