---
bolt: 044-generation-reliability
stage: test
created: 2026-09-17T21:55:00Z
status: acceptance-ready
---

# Test Report: Image Generation Service (Reliability)

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit (retry policy, usage accounting, idempotency fingerprint) | 9 | 0 | 0 | full branch coverage of both services |
| Integration (API + worker orchestration, Docker + Postgres) | 21 | 0 | 0 | all reliability code paths exercised |
| Regression (existing image-generation + full backend suite) | 381 | 0 | 0 | no regressions |
| Security (secret boundary on extended responses) | included above | - | - | - |
| **Total** | **381** | **0** | **0** | - |

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 003-provider-invocation-history | Status transitions persisted as queued/processing/completed/failed | ✅ `test_worker_success_records_invocation_and_usage`, `test_worker_no_result_is_terminal` |
| 003-provider-invocation-history | Attempts and reason visible on provider error; no secret stored | ✅ `test_worker_rate_limit_schedules_retry_and_keeps_job_queued`, `test_get_job_exposes_attempt_history_and_usage` |
| 003-provider-invocation-history | Completed job's durable result and configuration reference available for review | ✅ `test_get_job_exposes_attempt_history_and_usage` |
| 004-retry-idempotency-limits | Same idempotency key + payload returns one job | ✅ `test_same_idempotency_key_and_payload_returns_one_job` (single job id, single `send_task` call) |
| 004-retry-idempotency-limits | Duplicate delivery while an attempt is running starts no concurrent provider call | ✅ `test_worker_skips_when_lease_already_held` |
| 004-retry-idempotency-limits | 429 retries at most twice, honoring `Retry-After`; other errors do not auto-retry | ✅ `test_transient_error_retries_up_to_two_times_honoring_retry_after`, `test_terminal_error_never_retries`, `test_worker_rate_limit_schedules_retry_and_keeps_job_queued` |
| 004-retry-idempotency-limits | Same key + changed payload → conflict | ✅ `test_same_idempotency_key_different_payload_is_conflict` (409) |
| 005-usage-recording | Usage stored when provider reports it | ✅ `test_usage_reported_when_provider_returns_recognized_fields`, `test_worker_success_records_invocation_and_usage` |
| 005-usage-recording | Usage recorded as unknown, never zero, when provider is silent | ✅ `test_usage_unknown_when_provider_omits_usage`, `test_usage_unknown_not_zero_when_fields_unrecognized`, `test_worker_timeout_does_not_auto_retry` |
| 005-usage-recording | Usage viewable by staff without exposing the API key | ✅ `test_get_job_exposes_attempt_history_and_usage` (secret-boundary assertion on the extended response) |

## Unit Tests

`RetryPolicyService` (ADR-049 compliance): 429 classifies transient/retryable; other HTTP errors classify terminal; **timeout never auto-retries regardless of attempt number**; retry cap enforced at exactly 2 retries (3 total attempts), honoring `Retry-After` when present, falling back to a default delay otherwise.

`UsageAccountingService`: recognized usage fields → `reported`; absent usage → `unknown`; unrecognized/future provider fields → dropped and treated as `unknown` (never fabricated as zero).

`compute_payload_fingerprint`: stable regardless of input key ordering (required for idempotency matching).

## Integration Tests

Added `tests/test_image_generation_reliability.py` (21 tests) covering, against real Postgres in Docker:

- **Idempotency**: same key+payload returns the same job and enqueues exactly once; same key with a different payload returns 409.
- **Worker orchestration** (`_process_job`, provider mocked at the adapter boundary): success path records a `succeeded` invocation, uploads the result, and denormalizes usage onto the job; 429 records a `failed`/`transient` invocation, increments `retry_count`, and returns the job to `queued` with the computed delay; timeout records `timed_out` and leaves the job `failed` with **no retry scheduled**; no-result records a `terminal` invocation.
- **Duplicate-delivery guard**: a job whose status is not `queued` is skipped with zero invocations created; a job whose lease (`lock_token`) is already held is skipped the same way — both leave the provider adapter uncalled.
- **GET job detail**: `attempts` and `usage` reflect persisted invocation history; extended response still hides secrets (exact key-set assertion).
- **Manual retry endpoint**: allowed after a timeout (`error_category = transient`), rejected after a terminal error (409), rejected when no attempt has ever run (409).

Existing `test_image_generation_api.py`/`test_image_generation_task.py`/`test_image_generation_schema.py` (20 tests) updated only where the GET response contract intentionally grew (`attempts`, `usage`) and still pass.

## Security Tests

- Extended `GET` job response verified to expose exactly `{job_id, mode, provider, status, created_at, attempts, usage}` — no API key, no raw provider payload, in both the job fields and the attempt/usage sub-objects (ADR-047).
- `ProviderInvocation.usage_raw` is restricted to a whitelist of safe usage fields before persistence (`UsageAccountingService`); arbitrary provider response fields cannot reach the database.
- Retry endpoint is ownership-scoped (reuses `get_owned`) and staff-role gated, matching the existing job-detail authorization boundary.

## Performance Tests

Not applicable at this bolt's scope — no new latency-sensitive path was introduced beyond the existing job-creation/detail endpoints (unchanged p50/p95 characteristics; the only new endpoint, retry, performs the same shape of DB reads/writes as job creation).

## Coverage Report

All new modules (`retry_policy_service.py`, `usage_accounting_service.py`, `idempotency_service.py`, `concurrency_guard_service.py`, `provider_invocation_repo.py`, and the extended `tasks/image_generation.py` orchestration) are exercised by at least one direct test; every branch in `RetryPolicyService.decide` and `UsageAccountingService.normalize` has a dedicated case.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| `tasks/image_generation.py` imported `async_session` by value at module load, which would have silently bypassed the test database patch (`database.async_session` reassignment in `conftest.py`) | Medium | Fixed — switched to `import core.database as database` and a runtime lookup, matching `core/database.get_db`'s own pattern |

## Known Scope Boundary

The OpenAI adapter's real HTTP call (`services/image_generation_providers.py`) is implemented for **`text` mode only**. `edit`, `extraction`, and `try_on` (both `openai` and `vton`) raise a classified, non-retryable `PROVIDER_REQUEST_ERROR` — correctly recorded, correctly non-retried, no secret exposure — rather than guessing at image-resolution/composition logic that spans the media library owned by other units and was not part of this bolt's approved domain model or technical design. User confirmed this boundary at the Stage 4 checkpoint. Extending provider/mode coverage later requires no changes to the reliability layer verified here.

## Verification

| Command | Result |
|---|---|
| `pytest tests/test_image_generation_reliability.py tests/test_image_generation_api.py tests/test_image_generation_task.py tests/test_image_generation_schema.py -q` (Docker, test DB) | **41 passed** |
| `pytest -q` (full backend suite, Docker, test DB) | **381 passed** |
| `ruff check` (all new/changed files) | Passed |
| `alembic downgrade -1` then `alembic upgrade head` | Round-trips cleanly on the dev database |

## Ready for Operations

- [x] All acceptance criteria met
- [x] Code coverage: all new reliability modules have dedicated tests; full regression suite green
- [x] No critical/high severity issues open
- [x] Performance targets: not applicable (no new latency-sensitive path)
- [x] Security tests passing (secret boundary, ownership scoping)
