---
stage: test
bolt: 002-vton-job-service
created: 2026-05-26T23:55:00Z
---

# Test Report: 002-vton-job-service

## Summary

- **Unit Tests**: 12/12 passed
- **Integration Tests**: N/A (requires running PostgreSQL + RabbitMQ + Celery)
- **Security Tests**: Covered by unit tests (ownership isolation via service layer)
- **Performance Tests**: N/A for MVP

## Test Files

- [x] `tests/test_vton_job_service.py` — VTON job submission, status retrieval, provider factory

## Test Results

### VTONJobService (9 tests)

| Test | Status |
|------|--------|
| Submit job with own garment + own model | ✅ |
| Submit job with own garment + curated model | ✅ |
| Reject when garment not found | ✅ |
| Reject when garment belongs to another mayorista | ✅ |
| Reject when model not found | ✅ |
| Get job status with result URL (completed) | ✅ |
| Get job status without result URL (queued) | ✅ |
| Reject when job not found | ✅ |
| Reject when job belongs to another mayorista | ✅ |

### VTONProvider Factory (3 tests)

| Test | Status |
|------|--------|
| Get LocalGPUProvider when VTON_PROVIDER=local | ✅ |
| Get ReplicateProvider when VTON_PROVIDER=replicate | ✅ |
| Reject unknown provider type | ✅ |

## Acceptance Criteria Validation

### Story 001: Submit VTON Job

| Criteria | Status |
|----------|--------|
| POST `/api/vton/generate` returns `{ job_id, status: "queued", created_at }` | ✅ (unit test) |
| VTONJob record created with `status=queued` and `retry_count=0` | ✅ (unit test) |
| Celery task published after DB record committed | ✅ (unit test, mocked) |
| Invalid `cloth_type` → HTTP 400 | ✅ (Pydantic enum validation) |
| Garment belongs to another mayorista → HTTP 403 | ✅ (unit test) |
| Model not found → HTTP 404 | ✅ (unit test) |
| Not authenticated → HTTP 401 | ✅ (enforced by `Depends(get_current_mayorista)`) |

### Story 002: Process Job via Celery

| Criteria | Status |
|----------|--------|
| Worker transitions `queued → processing` with `started_at` | ✅ (task code) |
| On success: result stored in MinIO, `status=completed`, `result_minio_key` set | ✅ (task code) |
| Idempotency: worker skips if job not `queued` | ✅ (task code) |
| Result stored at `results/{mayorista_id}/{job_id}.jpg` | ✅ (task code) |

### Story 003: Poll Job Status

| Criteria | Status |
|----------|--------|
| GET `/api/vton/jobs/{job_id}` returns current status | ✅ (unit test) |
| Queued/processing: no `result_url` in response | ✅ (unit test) |
| Completed: `result_url` with fresh presigned URL | ✅ (unit test) |
| Job belongs to another mayorista → HTTP 403 | ✅ (unit test) |
| Job not found → HTTP 404 | ✅ (unit test) |
| Not authenticated → HTTP 401 | ✅ (enforced by `Depends(get_current_mayorista)`) |
| Fresh presigned URL generated per poll | ✅ (service code) |

## Coverage Notes

- Unit tests cover all service-layer logic: job submission, photo ownership validation, status retrieval
- Celery task tested via code review (requires running RabbitMQ + Celery for integration test)
- VTONProvider implementations tested via factory pattern (actual provider calls require GPU/Replicate API)
- Integration tests against real PostgreSQL + RabbitMQ + MinIO should be added before production deployment
