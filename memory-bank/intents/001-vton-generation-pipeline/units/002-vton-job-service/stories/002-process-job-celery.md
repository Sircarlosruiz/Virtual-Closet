---
id: 002-process-job-celery
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 002-vton-job-service
implemented: true
---

# Story: 002-process-job-celery

## User Story

**As a** Celery worker
**I want** to pick up a queued VTON job, call the AI provider, and store the result
**So that** the mayorista receives a generated try-on image

## Acceptance Criteria

- [ ] **Given** a job is in `status=queued`, **When** the Celery worker picks it up, **Then** `status` transitions to `processing` and `started_at` is set
- [ ] **Given** the worker is processing, **When** the `VTONProvider.generate()` call succeeds, **Then** the result image is stored in MinIO, `status` transitions to `completed`, `result_minio_key` is set, and `completed_at` is set
- [ ] **Given** the worker is processing, **When** `VTONProvider.generate()` raises an exception, **Then** the job is NOT immediately marked `failed` — retry logic handles it (see story 004)
- [ ] **Given** two workers compete for the same job, **When** one acquires it, **Then** only one worker processes it (idempotency via job status check before processing)
- [ ] **Given** the result is stored, **When** I check MinIO, **Then** the output image is at `results/{mayorista_id}/{job_id}.jpg`

## Technical Notes

- Celery task name: `process_vton_job`
- Worker must re-read job from DB at task start to confirm `status=queued` (guard against duplicate delivery)
- Provider call: `await vton_provider.generate(garment_url, model_url, cloth_type)`
- Garment and model URLs retrieved from MinIO (new pre-signed URLs generated at task time)
- Result stored at: `results/{mayorista_id}/{job_id}.jpg` in MinIO
- Status updates must be committed to DB before calling provider (so polls see `processing`)

## Dependencies

### Requires
- `002-vton-job-service/001-submit-vton-job` (job must exist in DB)

### Enables
- `002-vton-job-service/003-poll-job-status`
- `002-vton-job-service/004-retry-on-failure` (failure path)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job already `processing` when worker picks it up | Worker skips it (idempotency guard) |
| MinIO write fails after successful inference | Mark job `failed`, do not lose the inference result silently |
| Celery worker killed mid-task | Job stuck in `processing`; future: timeout detection |

## Out of Scope

- Timeout detection for stuck `processing` jobs (future enhancement)
- Result image post-processing
