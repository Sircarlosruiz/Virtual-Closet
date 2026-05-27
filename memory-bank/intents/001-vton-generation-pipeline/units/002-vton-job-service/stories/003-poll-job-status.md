---
id: 003-poll-job-status
unit: 002-vton-job-service
intent: 001-vton-generation-pipeline
status: complete
priority: must
created: 2026-05-26T00:00:00.000Z
assigned_bolt: 002-vton-job-service
implemented: true
---

# Story: 003-poll-job-status

## User Story

**As a** mayorista
**I want** to check the status of my VTON job
**So that** I know when my generated image is ready

## Acceptance Criteria

- [ ] **Given** I am authenticated and own the job, **When** I GET `GET /api/vton/jobs/{job_id}`, **Then** I receive the current job status and metadata
- [ ] **Given** the job is `queued` or `processing`, **When** I poll, **Then** response is `{ job_id, status, created_at, started_at }` — no `result_url`
- [ ] **Given** the job is `completed`, **When** I poll, **Then** response includes `result_url` (15-minute pre-signed MinIO URL) and `completed_at`
- [ ] **Given** the job is `failed`, **When** I poll, **Then** response includes `error_reason` and `retry_count`
- [ ] **Given** the job_id belongs to another mayorista, **When** I poll, **Then** I receive HTTP 403
- [ ] **Given** the job_id does not exist, **When** I poll, **Then** I receive HTTP 404
- [ ] **Given** I am not authenticated, **When** I poll, **Then** I receive HTTP 401
- [ ] **Given** the job is complete and I poll, **When** the response is returned, **Then** a new pre-signed URL is generated fresh (not cached)

## Technical Notes

- `result_url` is generated fresh per poll (pre-signed URLs are not stored in DB; only `result_minio_key` is)
- Response p95 < 200ms (simple DB read + optional presign)
- Ownership enforced in `vton_job_repo.get_by_id_and_mayorista(job_id, mayorista_id)`

## Dependencies

### Requires
- `002-vton-job-service/001-submit-vton-job`
- `002-vton-job-service/002-process-job-celery` (for completed/failed states)

### Enables
- `003-vton-pipeline-ui/004-job-status-polling-ui`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Poll immediately after submission | Returns `status=queued` |
| Poll after worker starts | Returns `status=processing` |
| Poll 16 minutes after job completes | Pre-signed URL may have expired — generate a new one per poll anyway |

## Out of Scope

- WebSocket or Server-Sent Events (polling only for MVP)
- Cancelling a running job
