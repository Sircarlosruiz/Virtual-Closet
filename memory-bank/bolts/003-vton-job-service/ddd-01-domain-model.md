---
unit: 002-vton-job-service
bolt: 003-vton-job-service
stage: model
status: complete
updated: 2026-05-27T00:05:00Z
---

# Static Model - VTON Job Service (Retry + History Extension)

## Bounded Context

**VTON Job Retry & History** — Extends the VTON job lifecycle with automatic retry on transient failures and paginated job history retrieval. This bolt builds on the `VTONJob` aggregate from bolt 002, adding retry state management and history query capabilities.

## Domain Entities (Extensions to bolt 002)

| Entity | New/Updated Properties | Business Rules |
|--------|----------------------|----------------|
| `VTONJob` | `retry_count` (int, default 0), `max_retries` (int, from env), `error_reason` (str, nullable) — **already created in bolt 002** | `retry_count` increments on each transient failure; when `retry_count >= max_retries`, job transitions to `failed`; non-retriable errors (4xx except 429) skip retries and go directly to `failed` |

## Value Objects (New)

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `RetryPolicy` | `max_retries` (int), `base_delay_seconds` (int), `max_delay_seconds` (int) | `max_retries` from `VTON_MAX_RETRIES` env (default 3); `base_delay_seconds` from `VTON_RETRY_BASE_DELAY_SECONDS` env (default 30); exponential backoff: `delay = min(base_delay * 2^retry_count, max_delay)` |
| `RetryableError` | `exception_type` (str), `is_retriable` (bool), `status_code` (int?) | Retriable: timeout, connection error, 429 (rate limit), 5xx server errors; Not retriable: 400 (bad input), 401 (auth), 403 (forbidden), 404 (not found) |

## Aggregates (Updated State Machine)

| Aggregate Root | Updated Members | Updated Invariants |
|----------------|-----------------|-------------------|
| `VTONJob` | `retry_count`, `max_retries`, `error_reason` — all already in schema | (7) On transient failure with `retry_count < max_retries`: status resets to `queued`, `retry_count` increments, job re-queued with backoff delay; (8) On transient failure with `retry_count >= max_retries`: status transitions to `failed`, `error_reason` set; (9) On non-retriable error: status transitions to `failed` immediately, `error_reason` set, no retry |

### Extended State Machine

```
queued ──► processing ──► completed
    │          │
    │          ├──► queued (retry, retry_count++)
    │          │
    │          └──► failed (non-retriable error or max retries exceeded)
    │
    └──► failed (manual/admin action — future)
```

**Retry transitions:**
- `processing → queued`: On retriable error with `retry_count < max_retries`
- `processing → failed`: On non-retriable error OR `retry_count >= max_retries`

## Domain Events (New)

| Event | Trigger | Payload |
|-------|---------|---------|
| `VTONJobRetryScheduled` | Transient failure with retries remaining | `job_id`, `retry_count`, `next_retry_delay_seconds` |
| `VTONJobPermanentlyFailed` | Max retries exceeded or non-retriable error | `job_id`, `error_reason`, `retry_count`, `is_retriable_error` |

## Domain Services (Updated)

| Service | New/Updated Operations | Dependencies |
|---------|----------------------|--------------|
| `VTONJobService` | `list_jobs(mayorista_id, page, page_size) → (list[VTONJob DTO], total)` — **new** | VTONJobRepo |
| `RetryPolicyService` | `get_retry_delay(retry_count) → int`; `is_retriable_error(exception) → bool` — **new** | Settings (env vars) |

## Repository Interfaces (Updated)

| Repository | New Methods |
|------------|-------------|
| `VTONJobRepo` | `list_by_mayorista(mayorista_id, page, page_size) → (list[VTONJob], total)` — **already created in bolt 002** |

## Ubiquitous Language (New Terms)

| Term | Definition |
|------|------------|
| **Retriable Error** | A transient failure that may succeed on retry: timeout, connection error, 429 (rate limit), 5xx server errors |
| **Non-Retriable Error** | A permanent failure that will not succeed on retry: 400 (bad input), 401 (auth), 403 (forbidden), 404 (not found) |
| **Exponential Backoff** | Retry delay strategy: `delay = base_delay * 2^retry_count`, capped at `max_delay` |
| **Retry Policy** | Configuration for retry behavior: max retries, base delay, max delay |
| **Job History** | Paginated list of a mayorista's VTON jobs, ordered by creation date (newest first) |
