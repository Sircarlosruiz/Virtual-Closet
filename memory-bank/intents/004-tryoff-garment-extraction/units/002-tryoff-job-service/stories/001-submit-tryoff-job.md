---
id: 001-submit-tryoff-job
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 016-tryoff-job-service
implemented: false
---

# Story: 001-submit-tryoff-job

## User Story

**As a** mayorista
**I want** to submit a garment extraction request with a source image and garment type
**So that** the system queues the job and I can track its progress

## Acceptance Criteria

- [ ] **Given** a valid source image (uploaded to media library) and garment_type (`upper`/`lower`/`dress`), **When** POST /api/tryoff/jobs is called, **Then** a TryoffJob record is created with status `pending` and the job is enqueued in Celery
- [ ] **Given** a valid request, **When** the job is created, **Then** the response includes `job_id`, `status: pending`, and `garment_type`
- [ ] **Given** an invalid garment_type, **When** POST /api/tryoff/jobs is called, **Then** it returns HTTP 422 with a descriptive error
- [ ] **Given** a non-existent source image ID, **When** the job is submitted, **Then** it returns HTTP 404
- [ ] **Given** a mayorista submits a job, **When** the response is returned, **Then** the job is owned by that mayorista (other mayoristas cannot access it)

## Technical Notes

- Endpoint: `POST /api/tryoff/jobs`
- Body: `{ source_image_id: uuid, garment_type: "upper" | "lower" | "dress" }`
- Creates `TryoffJob` in DB with status=`pending`, enqueues `process_tryoff_job.delay(job_id)`
- Reuse existing auth middleware for mayorista identity
- Source image must already exist in the media library (pre-validated)

## Dependencies

### Requires
- None (foundation story for this unit)

### Enables
- 002-process-job-celery
- 003-multi-garment-queue

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Rate limit (too many jobs in flight) | HTTP 429 (future — no limit for MVP) |
| Source image belongs to another mayorista | HTTP 404 (not exposed to caller) |
| Duplicate submission (same image + garment type within 60s) | Allowed — creates a new job |

## Out of Scope

- Actual Celery processing (story 002)
- Multi-garment queuing in one call (story 003)
