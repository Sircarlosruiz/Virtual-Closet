---
stage: test
bolt: 048-product-publication-sync
created: 2026-09-18T16:33:45Z
---

## Test Report: 003-product-image-integration

### Summary

- **Tests**: 12/12 passed (publication selection + sync delivery)
- **Prior contract**: 11/11 passed (`tests/test_integration_bridge.py`)
- **Regression**: 57/57 passed (`test_image_generation_api`, `test_image_generation_reliability`, `test_image_generation_schema`, `test_tenant_isolation`, `test_buyer_links`)
- **Coverage**: acceptance-path coverage (repo has no coverage gate); select/discard, dual delivery, partial failure, retry idempotency, and fail-closed branches exercised
- **Migration**: Alembic `upgrade head` → `downgrade -1` → `upgrade head` clean on PostgreSQL 16; head is `f6a7b8c9d0e1`

### Test Files

- [x] `backend/tests/test_publication_selection.py` - explicit select vs discard, append-only gallery, new composition version requires new selection, discarded history blocks retry, unknown link fail-closed, incomplete/blocked candidates, non-staff 403
- [x] `backend/tests/test_sync_delivery.py` - both destinations synced with configuration copy, BFashion failure isolated and retried without duplicate ProductImage or new generation job, non-retryable failure does not mark Virtual Closet failed, S2S publication, preview URL from durable key
- [x] `backend/tests/publication_helpers.py` - fake BFashion adapter and reminted preview URLs

### Acceptance Criteria Validation

- ✅ **Completed results can be selected or discarded; only selected candidates become deliveries**: `test_should_select_only_chosen_candidates_when_others_discarded` — selected job creates both destination rows and one gallery image; discarded job has no deliveries.
- ✅ **Publishing appends a gallery image; existing images are not replaced**: `test_should_append_gallery_image_when_publishing_another_candidate` — two selections produce two `ProductImage` rows with distinct keys and positions.
- ✅ **A new valid composition version is not published until a new explicit selection**: `test_should_require_new_selection_when_composition_version_changes` — v2 appears eligible with no decision; gallery count stays 1 after v1 was published.
- ✅ **Successful delivery stores image + configuration on both destinations with independent status**: `test_should_sync_both_destinations_when_delivery_succeeds` — both `synced`; configuration copy persisted; BFashion ingest received the durable key.
- ✅ **Duplicate delivery or retry does not create a second ProductImage, generation job, or OpenAI call**: `test_should_isolate_failed_destination_and_retry_without_duplicates` — retry then duplicate POST keep one image and the same job count; adapter called twice only for the failed destination.
- ✅ **A failed destination stays retryable without marking the other incorrectly**: same test plus `test_should_not_mark_other_destination_when_bfashion_fails_permanently` — Virtual Closet remains `synced` while BFashion is `failed` (retryable or not).
- ✅ **Expired preview/transfer URLs are recovered from the durable object key**: `test_preview_url_is_derived_from_durable_key` — preview is reminted from the stored key, not a previously issued URL.
- ✅ **Unknown, mismatched, or unauthorized product links fail closed**: `test_should_fail_closed_when_product_link_unknown`, `test_s2s_publication_uses_product_link_and_staff_assertion` (unknown external product 404), `test_should_forbid_non_staff_publication`.
- ✅ **Discarded results remain queryable and cannot be delivered while discarded**: `test_should_keep_discarded_historical_and_block_retry`.
- ✅ **Incomplete jobs and blocked composition versions cannot be selected**: `test_should_reject_incomplete_job_and_blocked_version`.

### Issues Found

None blocking.

- The BFashion ingest endpoint itself is still implemented in `~/dev/bfashion/ecommerce`; this bolt covers the outbound contract and a mockable adapter.
- Staff UI for review/retry is bolt 049.

### Notes

- Tests ran against a disposable PostgreSQL 16 instance (`TEST_DATABASE_URL` on port 5433). Host port 5432 was occupied by another project's database, which is why the default localhost credentials failed during implement.
- `ruff check` passes for every new/changed file in this bolt.
- Retry also recovers `pending` deliveries (crash after commit, before outbound), which is slightly broader than the plan's "failed only" wording and is covered by the retry path after a failed BFashion call.
