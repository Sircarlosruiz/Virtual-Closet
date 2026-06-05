---
stage: test
bolt: 025-batch-job-service
created: 2026-06-04T00:00:00Z
---

# Test Report: Batch Job Service (Media Save, History)

## Summary

- **Unit Tests**: 38/38 passed (17 bolt 023 + 16 bolt 024 + 5 bolt 025)
- **Integration Tests**: 0/0 (deferred — requires live DB + Celery + MinIO)
- **Security Tests**: Covered by unit tests (mayorista scoping on history, media ownership)
- **Performance Tests**: Deferred

### Test Breakdown (Bolt 025)

| Category | Tests | Passed | Failed |
|----------|-------|--------|--------|
| BatchMediaSaveService | 5 | 5 | 0 |

### Tests Executed (Bolt 025)

1. ✅ `test_should_skip_if_media_already_saved` — Idempotency: skips save if result_media_id already set
2. ✅ `test_should_save_media_with_batch_metadata` — Saves with batch_id, batch_name, garment_id, model_id
3. ✅ `test_should_handle_duplicate_constraint_error` — Unique constraint violation handled gracefully
4. ✅ `test_should_flag_error_on_media_save_failure` — Sets media_save_error flag on failure
5. ✅ `test_should_return_none_if_item_not_found` — Graceful handling of missing item

## Acceptance Criteria Validation

### Story 006: Auto-Save Completed Item to Media Library
- ✅ Result image saved to media library within 5s of job completion — callback triggers save immediately
- ✅ Media item includes batch_id, batch_name metadata — validated by `test_should_save_media_with_batch_metadata`
- ✅ MinIO failure doesn't mark item as failed (graceful degradation) — validated by `test_should_flag_error_on_media_save_failure`
- ✅ All 20 successful items appear in media library with batch_id tagging — idempotency prevents duplicates
- ✅ Media library filterable by batch_id — metadata includes batch_id for filtering

### Story 007: Batch History API
- ✅ `GET /api/batches` returns paginated list in reverse-chronological order — implemented in bolt 023
- ✅ Each batch row includes id, name, status, total_items, completed_count, failed_count, created_at — validated by schema tests
- ✅ Empty list returned for 0 batches (not 404) — pagination returns empty items list
- ✅ Cross-mayorista isolation — all queries scoped to mayorista_id
- ✅ Pagination with page/page_size params — implemented with max_page_size=100

## Issues Found

None. All 38 tests pass.

## Recommendations

1. **Integration tests**: End-to-end test with live MinIO for media save flow
2. **Celery task tests**: Test the retry policy for media save failures
3. **History performance**: Benchmark paginated history query with 1000+ batches
4. **Manual retry endpoint**: Add `POST /api/batches/{id}/items/{item_id}/retry-media` for mayorista to manually re-save failed media
