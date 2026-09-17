import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import core.database as database
from core.celery_app import app
from core.config import settings
from models.provider_invocation import ProviderInvocation
from repositories.generation_job_repo import GenerationJobRepository
from repositories.provider_invocation_repo import ProviderInvocationRepository
from services.concurrency_guard_service import ConcurrencyGuardService
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


def _get_provider(provider_name: str):
    if provider_name == "openai":
        return OpenAIImageProvider()
    raise ProviderRequestError(
        f"Provider '{provider_name}' execution is not yet wired to this worker"
    )


async def _process_job(job_id: UUID) -> int | None:
    """Runs one attempt; returns a retry delay (seconds) if a retry was scheduled."""
    async with database.async_session() as db:
        job_repo = GenerationJobRepository(db)
        invocation_repo = ProviderInvocationRepository(db)
        guard = ConcurrencyGuardService(job_repo)
        retry_policy = RetryPolicyService()
        usage_service = UsageAccountingService()

        job = await job_repo.get_by_id(job_id)
        if job is None:
            raise ValueError(f"GenerationJob {job_id} not found")

        if job.status != "queued":
            # Already processed, in flight, or terminal — duplicate delivery guard.
            logger.info("Skipping generation job %s: status is %s, not queued", job_id, job.status)
            return None

        lease = await guard.acquire(job_id)
        if lease is None:
            logger.warning(
                "Skipping generation job %s: concurrency lease already held", job_id
            )
            return None

        retry_delay: int | None = None
        try:
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
                return retry_delay
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
                return None
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
                return None

            # Success path.
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
            return None
        finally:
            await guard.release(lease)


@app.task(
    bind=True,
    name="tasks.generate_image",
    acks_late=True,
    queue="image.generation.normal",
)
def generate_image_task(self, job_id: str) -> None:
    """Worker entry point; only a job ID crosses the broker boundary (ADR-047)."""
    UUID(job_id)
    if not settings.OPENAI_API_KEY.strip():
        raise ValueError("Image generation is unavailable: provider is not configured")

    retry_delay = asyncio.run(_process_job(UUID(job_id)))
    if retry_delay is not None:
        self.retry(countdown=retry_delay)
