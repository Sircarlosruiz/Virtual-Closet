---
id: 002-process-job-celery
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 016-tryoff-job-service
implemented: false
---

# Story: 002-process-job-celery

## User Story

**As a** Celery worker
**I want** to pick up a TryOff job, call the model container, and persist the output
**So that** the extraction runs asynchronously and the result is stored without manual intervention

## Acceptance Criteria

- [ ] **Given** a `pending` TryoffJob is enqueued, **When** the Celery worker picks it up, **Then** job status transitions to `processing`
- [ ] **Given** the job is `processing`, **When** POST /tryoff on the model container succeeds, **Then** the output PNG is uploaded to MinIO and job status transitions to `complete` with `output_media_id` set
- [ ] **Given** the model container returns an error, **When** the Celery task fails, **Then** the job retries (handled by story 006); on final failure status becomes `failed`
- [ ] **Given** the job completes successfully, **When** a mayorista queries job status, **Then** `output_media_id` is present and the image is accessible via the media library

## Technical Notes

- Celery task: `process_tryoff_job(job_id: uuid)`
- Reads job from DB, fetches source image from MinIO, POSTs to `TRYOFF_MODEL_URL/tryoff`
- Uploads output PNG to MinIO at `extracted/{mayorista_id}/{job_id}.png`
- Creates MediaItem in DB with type=`extracted_garment`, metadata=`{garment_type, source_job_id}`
- Updates TryoffJob: status=`complete`, output_media_id=<new MediaItem id>
- Use httpx with timeout=120s for model container call

## Dependencies

### Requires
- 001-submit-tryoff-job (job must exist in DB)
- 001-tryoff-model-service/002-tryoff-inference-api (model container endpoint)

### Enables
- 004-poll-job-status
- 005-media-library-save

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Model container not healthy (503) | Task raises exception; Celery retry kicks in |
| MinIO upload fails | Task raises exception after output received; job retries |
| Job record deleted mid-processing | Task logs warning and exits gracefully |

## Out of Scope

- Retry logic (story 006)
- Media library metadata tagging details (story 005)
