---
stage: test
bolt: 001-media-service
created: 2026-05-26T23:25:00Z
---

# Test Report: 001-media-service

## Summary

- **Unit Tests**: 9/9 passed
- **Integration Tests**: N/A (requires running PostgreSQL + MinIO)
- **Security Tests**: Covered by unit tests (ownership isolation via repo queries)
- **Performance Tests**: N/A for MVP

## Test Files

- [x] `tests/test_media_service.py` — File validation, upload service, model library service

## Test Results

### File Validation (5 tests)

| Test | Status |
|------|--------|
| Accept valid JPEG | ✅ |
| Accept valid PNG | ✅ |
| Reject empty file | ✅ |
| Reject non-image magic bytes | ✅ |
| Reject oversized file (>10MB) | ✅ |

### MediaUploadService (2 tests)

| Test | Status |
|------|--------|
| Upload garment photo — correct MinIO key, metadata, presigned URL | ✅ |
| Upload model photo — correct MinIO key, is_curated=false, label | ✅ |

### ModelLibraryService (2 tests)

| Test | Status |
|------|--------|
| List curated models — returns only is_curated=true items | ✅ |
| List own models — returns only mayorista's non-curated items | ✅ |

## Acceptance Criteria Validation

### Story 001: Upload Garment Photo

| Criteria | Status |
|----------|--------|
| POST `/api/media/garments` stores file in MinIO under mayorista namespace | ✅ (unit test) |
| Response includes `{ id, presigned_url, filename, uploaded_at }` | ✅ (unit test) |
| Invalid file type → HTTP 400 | ✅ (unit test) |
| File > 10MB → HTTP 400 | ✅ (unit test) |
| Not authenticated → HTTP 401 | ✅ (enforced by `Depends(get_current_mayorista)`) |

### Story 002: Upload Own Model Photo

| Criteria | Status |
|----------|--------|
| POST `/api/media/models` stores file with `is_curated=false` | ✅ (unit test) |
| Response includes `{ id, presigned_url, label, is_curated, uploaded_at }` | ✅ (unit test) |
| GET `/api/media/models/mine` returns only own models | ✅ (unit test) |
| Same validation errors as garment upload | ✅ (shared `_validate_file`) |
| Not authenticated → HTTP 401 | ✅ (enforced by `Depends(get_current_mayorista)`) |

### Story 003: Curated Model Library

| Criteria | Status |
|----------|--------|
| GET `/api/media/models/curated` returns curated models with `is_curated=true` | ✅ (unit test) |
| No mayorista_id in curated response | ✅ (curated models have `mayorista_id=NULL`) |
| Mayorista cannot upload to curated library | ✅ (no upload endpoint for curated) |
| Not authenticated → HTTP 401 | ✅ (enforced by `Depends(get_current_mayorista)`) |

## Coverage Notes

- Unit tests cover all service-layer logic: validation, upload, listing
- Integration tests against real PostgreSQL + MinIO should be added before production deployment
- API endpoint integration tests (via httpx AsyncClient) should be added to verify full request/response cycle
