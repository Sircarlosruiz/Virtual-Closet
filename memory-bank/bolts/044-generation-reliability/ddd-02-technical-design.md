---
stage: design
bolt: 044-generation-reliability
created: 2026-09-17T16:55:00Z
---

# Technical Design: Image Generation Service (Reliability)

## Architecture Pattern

Continues the layered pattern from bolt 043 (router → service → repository →
model, with a Celery worker at the infrastructure edge). Reliability concerns
are added as dedicated domain services rather than embedded inline in the
router or the worker task, so retry/idempotency/concurrency/usage logic is
independently testable and does not leak into HTTP or queue plumbing.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  image_generation router (extended): retry endpoint,
│                              │  job detail response includes attempt history + usage
├─────────────────────────────┤
│      Application            │  image_generation_service (extended): idempotent
│                              │  submission; manual retry use case
├─────────────────────────────┤
│        Domain               │  RetryPolicyService, IdempotencyService,
│                              │  ConcurrencyGuardService, UsageAccountingService
├─────────────────────────────┤
│     Infrastructure          │  provider_invocation_repo, generation_job_repo
│                              │  (extended), Celery task (extended)
└─────────────────────────────┘
```

## Components

| Layer | Component | Responsibility |
|---|---|---|
| Model | `models/provider_invocation.py` | SQLAlchemy persistence for `ProviderInvocation` |
| Model | `models/generation_job.py` (extended) | Adds idempotency, retry, and usage columns |
| Repository | `repositories/provider_invocation_repo.py` | Invocation history CRUD, find-pending |
| Repository | `repositories/generation_job_repo.py` (extended) | Idempotency lookup, retry-count increment, usage update, lease acquire/release |
| Service | `services/idempotency_service.py` | Resolve-or-create job by `(key, payload_fingerprint)`; conflict detection |
| Service | `services/retry_policy_service.py` | Classify provider outcome; decide retry vs terminal |
| Service | `services/concurrency_guard_service.py` | Acquire/release the per-job execution lease |
| Service | `services/usage_accounting_service.py` | Normalize provider usage into `UsageRecord` |
| Schema | `api/schemas/image_generation.py` (extended) | Adds `idempotency_key` request field, `attempts`/`usage` response fields |
| Router | `api/routers/image_generation.py` (extended) | `POST .../{job_id}/retry`; job detail includes history + usage |
| Worker | `tasks/image_generation.py` (extended) | Acquires lease, invokes provider, classifies outcome, records invocation, applies retry decision, records usage |

## API Design

| Endpoint | Method | Request | Response |
|---|---|---|---|
| `POST /api/image-generation/jobs` (extended) | POST | Existing body + optional `Idempotency-Key` header | 202 with `job_id` (existing job if key+payload match), 409 if key matches with a different payload |
| `GET /api/image-generation/jobs/{job_id}` (extended) | GET | — | Existing fields + `attempts: [{attempt_number, status, error_code, started_at, completed_at}]` + `usage: {status, model, call_count}` |
| `POST /api/image-generation/jobs/{job_id}/retry` | POST | — (staff-only) | 202 if a new attempt is created; 409 if the job is not in a retryable state (already succeeded, lease held, or terminal without staff override) |

Attempt and usage fields returned are restricted to the safe subset defined
in the domain model — no raw provider request/response, no credentials.

## Data Persistence

| Table | Columns | Relationships |
|---|---|---|
| `provider_invocations` (new) | `id` (UUID PK), `job_id` (FK), `attempt_number` (int), `provider`, `model`, `status` (check: pending/succeeded/failed/timed_out), `error_code`, `error_category`, `retryable`, `started_at`, `completed_at`, `usage_status`, `usage_model`, `usage_call_count`, `usage_raw` (JSONB, sanitized) | Many invocations per `generation_jobs` row; unique on `(job_id, attempt_number)` |
| `generation_jobs` (extended) | + `idempotency_key` (nullable), `payload_fingerprint` (nullable), `retry_count` (int, default 0), `lock_token` (nullable), `locked_at` (nullable), `usage_status` (default `unknown`), `usage_model` (nullable), `usage_call_count` (nullable) | Composite unique index on `(idempotency_key, payload_fingerprint)` where `idempotency_key IS NOT NULL` |

`lock_token`/`locked_at` implement the `ConcurrencyLease` as an atomic
conditional `UPDATE ... WHERE lock_token IS NULL`, following the same
atomic-update pattern already used for batch counters (ADR-009,
ADR-021) rather than introducing a new locking primitive.

## Idempotency & Conflict Handling

1. Caller submits `Idempotency-Key` header; the service computes
   `payload_fingerprint` from the normalized, validated request body.
2. `IdempotencyService.resolve_or_create` looks up `(key, payload_fingerprint)`:
   - Match found → return the existing `job_id` (no new job, no new enqueue).
   - Key exists with a different fingerprint → `409 Conflict`.
   - No match → proceed with normal job creation from bolt 043 (commit
     before enqueue, per ADR-048), storing the key and fingerprint.
3. Omitting the header is allowed; such jobs are never idempotency-matched.

## Concurrency & Retry Handling

1. Before invoking the provider, the worker attempts
   `ConcurrencyGuardService.acquire(job_id)` via the atomic `lock_token`
   update. Failure to acquire (lease already held) exits the task
   immediately with no provider call and no state change — this is the
   duplicate-delivery safeguard.
2. On completion (success or failure), the worker releases the lease and
   records a `ProviderInvocation` row via `ProviderInvocationRepository`.
3. `RetryPolicyService.classify` maps the outcome:
   - HTTP 429 or connection timeout → `transient`.
   - Any other error status → `terminal`.
   - No response received before the worker's own timeout → `timed_out`
     (usage `unknown`), classified separately from `failed`.
4. `RetryPolicyService.decide`:
   - `transient` and `retry_count < 2` → schedule a Celery retry honoring
     `Retry-After` when present (otherwise a fixed short backoff).
   - `terminal`, or `transient` with retry budget exhausted → job moves to
     `failed`, `GenerationJobExhausted` semantics apply.
   - `timed_out` → **no automatic Celery retry** (a blind retry could
     duplicate a provider call that actually completed). The job is left in
     a state that surfaces the ambiguous outcome to staff, who can invoke
     `POST .../retry` to explicitly start a new attempt once they've
     confirmed no duplicate is desired.

## Usage Accounting

- `UsageAccountingService.normalize` reads only recognized fields from the
  provider response; anything absent yields `usage_status = unknown` on
  both the `ProviderInvocation` and the denormalized `generation_jobs`
  usage columns — never a zero.
- Usage is written once, from the invocation that completes the job
  (`succeeded`, or the final `failed`/`timed_out` attempt if the provider
  reported partial usage before erroring).

## Security Design

| Concern | Approach |
|---|---|
| Authentication | Reuses existing `get_current_mayorista` staff dependency (unchanged from bolt 043) |
| Authorization | Retry endpoint restricted to the job's owning staff account, same ownership check as job detail |
| Secret handling | No invocation or job column stores a provider credential; `usage_raw` and `error_code` are whitelisted/sanitized before persistence, per ADR-047 |
| Logging | Retry and lease-refusal events log at `warn` per `core/logger.py` conventions; no raw provider error text or usage payload is logged |

## NFR Implementation

| Requirement | Design Approach |
|---|---|
| Reliability | Attempt history is append-only and independent of job status, so job state can always be reconstructed from invocations; concurrency lease makes reconciliation retries (ADR-048) safe |
| Cost control | Concurrency lease bounds in-flight provider calls per job to one; retry cap (2) bounds duplicate spend on transient errors; manual-only retry on timeout avoids double-billing ambiguous outcomes |
| Observability | Attempt history and usage are queryable per job without exposing secrets, satisfying story 003's audit need |

## Error Handling

| Error Type | Code | Response |
|---|---|---|
| Idempotency key reused with different payload | `IDEMPOTENCY_CONFLICT` | 409 |
| Retry requested while lease held or job already terminal-succeeded | `RETRY_NOT_ALLOWED` | 409 |
| Provider 429 | `PROVIDER_RATE_LIMITED` (transient) | Job stays `processing`; auto-retry per policy |
| Provider timeout | `PROVIDER_TIMEOUT` (unknown outcome) | Job surfaces ambiguous state; no auto-retry |
| Provider other 4xx/5xx | `PROVIDER_ERROR` (terminal) | Job → `failed`, no retry |

## External Dependencies

| Service | Purpose | Integration |
|---|---|---|
| OpenAI Image API | Provider invocation being tracked | Existing adapter from bolt 043; this bolt only wraps its outcome in classification/retry/usage handling |
| PostgreSQL | Durable invocation history, idempotency index, lease column | Existing `AsyncSession` pattern |
| Celery/RabbitMQ | Retry scheduling via `countdown`/`max_retries` | Existing worker from bolt 043, extended |

## Compatibility

No changes to the bolt 043 provider protocol, mode/provider validation, or
existing VTON flows. `generation_jobs` columns are additive and nullable;
existing jobs without an idempotency key or invocation history remain valid.
