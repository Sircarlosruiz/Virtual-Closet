---
id: 006-retry-on-failure
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: should
created: 2026-05-31T00:00:00Z
assigned_bolt: 017-tryoff-job-service
implemented: false
---

# Story: 006-retry-on-failure

## User Story

**As a** mayorista
**I want** failed extraction jobs to automatically retry
**So that** transient model or network errors don't require me to resubmit

## Acceptance Criteria

- [ ] **Given** a Celery task fails with a transient error (model 503, timeout, MinIO error), **When** the task exits with an exception, **Then** it retries automatically up to 2 times with exponential backoff (30s, 60s)
- [ ] **Given** all retries are exhausted, **When** the third attempt also fails, **Then** the TryoffJob status is set to `failed` and `error_message` contains the last exception message
- [ ] **Given** the job is retrying, **When** the status is polled, **Then** it shows `processing` (not a distinct `retrying` state for MVP)
- [ ] **Given** a retry succeeds, **When** the job completes, **Then** it is treated as a normal completion — no retry count exposed in the response

## Technical Notes

- Celery task decorator: `@app.task(bind=True, max_retries=2, default_retry_delay=30)`
- On exception: `self.retry(exc=exc, countdown=30 * (self.request.retries + 1))`
- Only retry on: `httpx.TimeoutException`, `httpx.HTTPStatusError` (5xx), `MinIO connection errors`
- Do NOT retry on: HTTP 4xx from model container (client error), validation errors
- Same pattern as VTON pipeline (002-vton-job-service/004-retry-on-failure)

## Dependencies

### Requires
- 002-process-job-celery

### Enables
- Production reliability

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Model returns HTTP 400 (bad prompt) | Not retried — job fails immediately with error |
| Retry succeeds on attempt 2 | Job marked complete; retry count not shown to user |
| Worker restarted during retry countdown | Celery reschedules after worker comes back up |

## Out of Scope

- Dead letter queue for permanently failed jobs
- Manual retry trigger from UI (user re-submits instead)
