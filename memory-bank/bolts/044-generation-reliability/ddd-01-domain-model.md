---
stage: model
bolt: 044-generation-reliability
created: 2026-09-17T16:45:00Z
---

## Static Model: Image Generation Service (Reliability)

## Bounded Context

Extends the `GenerationJob` aggregate established in bolt 043 with durable
attempt history, safe retries, idempotency, concurrency limits, and usage
accounting. This bolt does not redefine job creation, mode/provider
validation, or the API contract for submitting jobs — it governs what happens
between "queued" and a terminal status, and what is recorded along the way.

### Entities

- **GenerationJob** (existing aggregate root, extended): adds `idempotency_key`,
  `payload_fingerprint`, `retry_count`, `usage_status` (`unknown` until a
  terminal attempt reports otherwise) - Business Rules: a job is created at
  most once per `(idempotency_key, payload_fingerprint)` pair; `retry_count`
  only advances through the retry policy, never by direct client action;
  `usage_status` starts `unknown` and is never defaulted to zero.
- **ProviderInvocation**: `id`, `job_id`, `attempt_number`, `provider`,
  `model`, `status` (`pending`, `succeeded`, `failed`, `timed_out`),
  `started_at`, `completed_at`, `error_classification`, `usage` - Business
  Rules: attempt numbers are sequential starting at 1 per job; at most one
  invocation per job may be `pending` at any time; a `timed_out` invocation
  has an outcome of "unknown" (not "failed") until reconciled; no invocation
  record may contain the provider credential, raw request body, or raw
  response body — only sanitized, safe fields.

### Value Objects

- **IdempotencyKey**: `key` (caller-supplied), `payload_fingerprint`
  (deterministic hash of the normalized job request) - Constraints: same
  `key` with the same `payload_fingerprint` resolves to the same job; same
  `key` with a different `payload_fingerprint` is a conflict, never a silent
  overwrite.
- **ErrorClassification**: `code` (safe, enumerable), `category`
  (`transient` | `terminal`), `retryable` (bool) - Constraints: derived only
  from provider status codes/timeouts, never from raw provider error text;
  `429` and connection timeout classify as `transient`; all other 4xx
  classify as `terminal`.
- **RetryDecision**: `should_retry` (bool), `delay`, `next_attempt_number` -
  Constraints: at most 2 retries total for `transient` classification; delay
  honors provider `Retry-After` when present; `terminal` classification and
  exhausted retry budget both yield `should_retry = false`.
- **UsageRecord**: `model`, `call_count`, `raw_usage` (sanitized subset),
  `status` (`reported` | `unknown`) - Constraints: `status` is `unknown`
  whenever the provider response omits usage data; `unknown` is never
  coerced to zero; unrecognized/future provider usage fields are dropped,
  not guessed at.
- **ConcurrencyLease**: `job_id`, `holder_token`, `acquired_at` - Constraints:
  at most one active lease per job; a second acquisition attempt while a
  lease is held fails closed (no provider call is started), it does not
  queue silently behind the first.

### Aggregates

- **GenerationJob** (root, extended boundary): Members: `ProviderInvocation`
  history (0..N, append-only), `IdempotencyKey`, `usage_status` - Invariants:
  (1) the set of `ProviderInvocation` rows is the sole source of truth for
  attempts and errors — nothing about attempt history is inferred from job
  status alone; (2) a job transitions to `failed` only when the latest
  invocation is `terminal` or the retry budget is exhausted; (3) a job's
  final `UsageRecord` is set from the completing invocation's usage, or
  marked `unknown` if that invocation reported none; (4) duplicate delivery
  of the same queue message must observe the `ConcurrencyLease` and must not
  start a second provider call for the same job.

### Domain Events

- **ProviderInvocationStarted**: Trigger: worker begins an attempt - Payload:
  `job_id`, `attempt_number`, `provider`, `model`.
- **ProviderInvocationSucceeded**: Trigger: provider call returns a usable
  result - Payload: `job_id`, `attempt_number`, `usage` (with `status`).
- **ProviderInvocationFailed**: Trigger: provider call errors, times out, or
  is classified terminal - Payload: `job_id`, `attempt_number`,
  `error_classification`.
- **RetryScheduled**: Trigger: `RetryDecision.should_retry` is true - Payload:
  `job_id`, `next_attempt_number`, `delay`.
- **GenerationJobExhausted**: Trigger: retry budget exhausted or terminal
  classification reached with no further retries - Payload: `job_id`,
  `final_error_classification`.
- **UsageRecorded**: Trigger: job reaches a terminal status - Payload:
  `job_id`, `provider`, `model`, `usage_status`.

### Domain Services

- **RetryPolicyService**: Operations: `classify(providerResponseOrTimeout)`,
  `decide(job, invocation)` → `RetryDecision` - Dependencies:
  `ProviderInvocationRepository` (attempt count), clock (for `Retry-After`
  delay math).
- **IdempotencyService**: Operations: `resolveOrCreate(idempotencyKey,
  payloadFingerprint)` → existing job or new job, `detectConflict(...)` -
  Dependencies: `GenerationJobRepository`.
- **ConcurrencyGuardService**: Operations: `acquire(job_id)` →
  `ConcurrencyLease` or refusal, `release(lease)` - Dependencies: a
  single-writer lock primitive (row-level lock or equivalent); must fail
  closed, never fail open, on lock-backend unavailability.
- **UsageAccountingService**: Operations: `normalize(rawProviderUsage)` →
  `UsageRecord` - Dependencies: none beyond the provider response passed in;
  must never fabricate a numeric value where the provider is silent.

### Repository Interfaces

- **ProviderInvocationRepository**: Entity: `ProviderInvocation` - Methods:
  `create(invocation)`, `listByJob(job_id)`, `findPending(job_id)`,
  `markCompleted(id, status, error_classification, usage)`.
- **GenerationJobRepository** (extended from bolt 043): Entity:
  `GenerationJob` - Methods added: `findByIdempotencyKey(key)`,
  `incrementRetryCount(job_id)`, `updateUsageStatus(job_id, usageRecord)`.

### Ubiquitous Language

- **Attempt**: One execution try against a provider, recorded as a
  `ProviderInvocation`.
- **Idempotency Key**: Caller-supplied token guaranteeing at most one job per
  `(key, payload)` pair.
- **Concurrency Lease**: The exclusive right to execute a provider call for a
  job at a given moment; prevents duplicate delivery from producing a second
  in-flight call.
- **Transient Error**: A retryable failure — `429` or timeout.
- **Terminal Error**: A non-retryable failure that ends the job without
  further attempts.
- **Usage Unknown**: The explicit state recorded when a provider does not
  report usage, distinct from and never conflated with zero usage.

## State Transitions (Attempt-Level, within GenerationJob lifecycle)

```text
pending -> succeeded
       \-> failed (terminal)          -> GenerationJobExhausted
       \-> timed_out (unknown outcome) -> RetryScheduled | GenerationJobExhausted
```

The job-level lifecycle (`queued -> processing -> completed|failed`) from
bolt 043 is unchanged. This bolt governs what happens *inside* `processing`:
each `ProviderInvocation` is one pass through the diagram above, and the job
only reaches a terminal status once its invocation history says so.

## Boundaries

- `ProviderInvocationRepository` and the extended `GenerationJobRepository`
  own persistence; no invocation or job field may hold a provider secret,
  raw request, or raw response body.
- `RetryPolicyService`, `IdempotencyService`, `ConcurrencyGuardService`, and
  `UsageAccountingService` own reliability decisions; the worker/task layer
  calls into them rather than embedding retry/idempotency logic inline.
- This bolt directly supports the reconciliation risk noted in ADR-048
  (commit-before-enqueue): the `ConcurrencyGuardService` and
  `IdempotencyService` are the mechanisms that make a reconciliation retry
  safe against duplicate provider calls.
- Provider credential resolution remains inside the worker per ADR-047; no
  entity or value object introduced here carries a credential.
