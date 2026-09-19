import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import core.database as database
from core.celery_app import app
from core.config import settings
from models.provider_invocation import ProviderInvocation
from repositories.generation_job_repo import GenerationJobRepository
from repositories.provider_invocation_repo import ProviderInvocationRepository
from services.concurrency_guard_service import ConcurrencyGuardService
from services.credential_gate_service import CredentialGateService, CredentialMissingError
from services.global_concurrency_service import (
    GlobalConcurrencyService,
    RedisUnavailableError,
)
from services.image_generation.replicate_tryon_adapter import ReplicateTryOnAdapter
from services.image_generation_providers import (
    OpenAIImageProvider,
    ProviderNoResultError,
    ProviderRateLimitedError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from services.retry_policy_service import RetryPolicyService
from services.storage_service import StorageService
from services.usage_accounting_service import UsageAccountingService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobProcessResult:
    retry_delay: int | None = None
    reschedule_slot_wait: bool = False


def _get_provider(provider_name: str):
    if provider_name == "openai":
        return OpenAIImageProvider()
    if provider_name == "replicate":
        return ReplicateTryOnAdapter()
    raise ProviderRequestError(
        f"Provider '{provider_name}' execution is not yet wired to this worker"
    )


def _global_concurrency_service() -> GlobalConcurrencyService:
    return GlobalConcurrencyService()


def _slot_wait_exhausted(job) -> bool:
    started = job.concurrency_wait_started_at
    if started is None:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return elapsed > settings.IMAGE_GENERATION_SLOT_WAIT_MAX_SECONDS


async def _fail_job(job_repo: GenerationJobRepository, job_id: UUID, error_code: str) -> None:
    await job_repo.update_status(job_id, status="failed", error_code=error_code)


async def _process_job(job_id: UUID) -> JobProcessResult:
    """Runs one attempt; may request a provider retry or a slot-wait reschedule."""
    async with database.async_session() as db:
        job_repo = GenerationJobRepository(db)
        invocation_repo = ProviderInvocationRepository(db)
        guard = ConcurrencyGuardService(job_repo)
        retry_policy = RetryPolicyService()
        usage_service = UsageAccountingService()
        gate = CredentialGateService()
        pool = _global_concurrency_service()

        job = await job_repo.get_by_id(job_id)
        if job is None:
            raise ValueError(f"GenerationJob {job_id} not found")

        if job.status != "queued":
            logger.info("Skipping generation job %s: status is %s, not queued", job_id, job.status)
            return JobProcessResult()

        try:
            gate.require(job.provider)
        except CredentialMissingError as exc:
            classification = retry_policy.classify_credential_missing()
            logger.warning("Generation job %s missing credential for %s", job_id, exc.provider)
            await _fail_job(job_repo, job_id, classification.code)
            return JobProcessResult()
        except ProviderRequestError:
            classification = retry_policy.classify_request_error()
            await _fail_job(job_repo, job_id, classification.code)
            return JobProcessResult()

        if _slot_wait_exhausted(job):
            classification = retry_policy.classify_concurrency_wait_exhausted()
            await _fail_job(job_repo, job_id, classification.code)
            return JobProcessResult()

        lease = await guard.acquire(job_id)
        if lease is None:
            logger.warning(
                "Skipping generation job %s: concurrency lease already held", job_id
            )
            return JobProcessResult()

        slot_held = False
        call_started = False
        retry_delay: int | None = None
        try:
            try:
                slot_held = await pool.try_acquire(job_id)
            except RedisUnavailableError:
                logger.warning(
                    "Redis unavailable for job %s — fail-closed, rescheduling slot wait",
                    job_id,
                )
                slot_held = False

            if not slot_held:
                await guard.release(lease)
                lease = None
                await job_repo.ensure_concurrency_wait_started(job_id)
                refreshed = await job_repo.get_by_id(job_id)
                if refreshed is not None and _slot_wait_exhausted(refreshed):
                    classification = retry_policy.classify_concurrency_wait_exhausted()
                    await _fail_job(job_repo, job_id, classification.code)
                    return JobProcessResult()
                logger.info("Generation job %s waiting for global concurrency slot", job_id)
                return JobProcessResult(reschedule_slot_wait=True)

            await job_repo.record_provider_call_started(job_id)
            call_started = True

            attempt_number = await invocation_repo.count_by_job(job_id) + 1
            invocation = await invocation_repo.create(
                ProviderInvocation(
                    job_id=job_id,
                    attempt_number=attempt_number,
                    provider=job.provider,
                    status="pending",
                )
            )
            await job_repo.update_status(job_id, status="processing")

            try:
                provider = _get_provider(job.provider)
                result = await provider.generate(job.input_data)
            except ProviderRateLimitedError as exc:
                classification = retry_policy.classify_http_error(429)
                await invocation_repo.mark_completed(
                    invocation.id,
                    "failed",
                    classification.code,
                    classification.category,
                    classification.retryable,
                    "unknown",
                    None,
                    None,
                    None,
                    datetime.now(timezone.utc),
                )
                decision = retry_policy.decide(
                    classification, attempt_number, exc.retry_after_seconds
                )
                if decision.should_retry:
                    await job_repo.increment_retry_count(job_id)
                    await job_repo.update_status(
                        job_id, status="queued", error_code=classification.code
                    )
                    retry_delay = decision.delay_seconds
                else:
                    await job_repo.update_status(
                        job_id, status="failed", error_code=classification.code
                    )
                return JobProcessResult(retry_delay=retry_delay)
            except ProviderTimeoutError:
                classification = retry_policy.classify_timeout()
                await invocation_repo.mark_completed(
                    invocation.id,
                    "timed_out",
                    classification.code,
                    classification.category,
                    classification.retryable,
                    "unknown",
                    None,
                    None,
                    None,
                    datetime.now(timezone.utc),
                )
                await job_repo.update_status(
                    job_id, status="failed", error_code=classification.code
                )
                logger.warning(
                    "Generation job %s timed out; outcome unknown, manual retry required",
                    job_id,
                )
                return JobProcessResult()
            except (ProviderNoResultError, ProviderRequestError) as exc:
                classification = (
                    retry_policy.classify_no_result()
                    if isinstance(exc, ProviderNoResultError)
                    else retry_policy.classify_request_error()
                )
                await invocation_repo.mark_completed(
                    invocation.id,
                    "failed",
                    classification.code,
                    classification.category,
                    classification.retryable,
                    "unknown",
                    None,
                    None,
                    None,
                    datetime.now(timezone.utc),
                )
                await job_repo.update_status(
                    job_id, status="failed", error_code=classification.code
                )
                return JobProcessResult()

            usage_record = usage_service.normalize(result.provider_model, result.usage)
            result_key = f"generated/{job.owner_id}/{job_id}.png"
            storage = StorageService()
            await storage.upload_bytes(
                result_key,
                result.image_bytes,
                content_type="image/png",
                bucket_override="generated",
            )
            await invocation_repo.mark_completed(
                invocation.id,
                "succeeded",
                None,
                None,
                None,
                usage_record.status,
                usage_record.model,
                usage_record.call_count,
                usage_record.raw,
                datetime.now(timezone.utc),
            )
            await job_repo.update_status(job_id, status="completed", result_key=result_key)
            await job_repo.update_usage(
                job_id, usage_record.status, usage_record.model, usage_record.call_count
            )
            return JobProcessResult()
        finally:
            if call_started:
                await job_repo.record_execution_seconds(job_id)
            if slot_held:
                await pool.release(job_id)
            if lease is not None:
                await guard.release(lease)


_CELERY_TIME_LIMIT = (
    settings.IMAGE_GENERATION_REPLICATE_TIMEOUT_SECONDS
    + settings.IMAGE_GENERATION_CELERY_TIME_LIMIT_BUFFER_SECONDS
)
_CELERY_SOFT_TIME_LIMIT = max(_CELERY_TIME_LIMIT - 15, 1)


@app.task(
    bind=True,
    name="tasks.generate_image",
    acks_late=True,
    queue="image.generation.normal",
    time_limit=_CELERY_TIME_LIMIT,
    soft_time_limit=_CELERY_SOFT_TIME_LIMIT,
)
def generate_image_task(self, job_id: str) -> None:
    """Worker entry point; only a job ID crosses the broker boundary (ADR-047)."""
    UUID(job_id)
    result = asyncio.run(_process_job(UUID(job_id)))
    if result.reschedule_slot_wait:
        self.apply_async(
            args=[job_id],
            countdown=settings.IMAGE_GENERATION_SLOT_RETRY_COUNTDOWN_SECONDS,
        )
        return
    if result.retry_delay is not None:
        self.retry(countdown=result.retry_delay)
