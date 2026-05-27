---
id: 004-retry-on-failure
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
status: draft
priority: must
created: 2026-05-26T00:00:00Z
assigned_bolt: 003-vton-job-service
implemented: false
---

# Story: 004-retry-on-failure

## User Story

**As a** system
**I want** to automatically retry failed VTON inference attempts
**So that** transient provider errors do not permanently fail a mayorista's job

## Acceptance Criteria

- [ ] **Given** `VTONProvider.generate()` raises an exception, **When** `retry_count < max_retries`, **Then** the job is re-queued with `retry_count` incremented and `status` reset to `queued`
- [ ] **Given** the job is re-queued, **When** it is retried, **Then** exponential backoff is applied (e.g., 30s, 60s, 120s delays)
- [ ] **Given** `retry_count == max_retries` and the attempt fails again, **When** the worker processes it, **Then** `status` is set to `failed`, `error_reason` is set to the last exception message
- [ ] **Given** a job reaches `failed` after all retries, **When** a mayorista polls it, **Then** they see `status=failed` and `error_reason`
- [ ] **Given** `max_retries` is set via env var `VTON_MAX_RETRIES` (default: 3), **When** the system starts, **Then** all jobs use this configured value

## Technical Notes

- Implement via Celery's `autoretry_for` + `max_retries` + `default_retry_delay` OR manual retry logic in the task
- Exponential backoff: delay = `base_delay * (2 ** retry_count)` seconds
- `base_delay` configurable via `VTON_RETRY_BASE_DELAY_SECONDS` env var (default: 30)
- `max_retries` configurable via `VTON_MAX_RETRIES` env var (default: 3)
- Retry count tracked in `vton_jobs.retry_count` column (not only in Celery)
- Replicate 429 (rate limit) should be retried with longer backoff; other 4xx errors should NOT be retried

## Dependencies

### Requires
- `002-vton-job-service/002-process-job-celery` (failure path from processing)

### Enables
- `003-vton-pipeline-ui/004-job-status-polling-ui` (failed state display)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Replicate returns 429 (rate limit) | Retry with longer backoff |
| Replicate returns 400 (bad input) | Do NOT retry — immediately fail with error_reason |
| Worker killed during retry wait | Celery re-delivers after visibility timeout |
| `max_retries=0` (no retries) | First failure → immediately `failed` |

## Out of Scope

- Manual retry triggered by mayorista (auto-retry only for MVP)
- Dead-letter queue for permanently failed messages
