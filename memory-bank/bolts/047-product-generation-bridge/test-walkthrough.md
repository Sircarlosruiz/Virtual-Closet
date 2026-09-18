---
stage: test
bolt: 047-product-generation-bridge
created: 2026-09-18T15:36:06Z
---

## Test Report: 003-product-image-integration

### Summary

- **Tests**: 11/11 passed (`tests/test_integration_bridge.py`)
- **Regression**: 57/57 passed (`test_image_generation_api`, `test_image_generation_reliability`, `test_image_generation_schema`, `test_tenant_isolation`, `test_buyer_links`)
- **Coverage**: acceptance-path coverage (repo has no coverage gate); every accepted and rejected branch exercised
- **Migration**: Alembic `upgrade head` → `downgrade -1` → `upgrade head` clean on PostgreSQL 16

### Test Files

- [x] `backend/tests/test_integration_bridge.py` - accepted creation, unknown/inactive/mismatched/cross-tenant link rejection, non-staff rejection, invalid credentials, owner-scoped status, idempotent replay and conflict

### Acceptance Criteria Validation

- ✅ **Given an authorized staff request from either application, when product and wholesaler links are valid, then Virtual Closet creates the job**: `test_bridge_creates_job_for_valid_link` asserts 202, `queued`, correct owner and single Celery enqueue.
- ✅ **Given an unknown, mismatched or unauthorized product link, when requested, then the operation fails closed**: `test_bridge_rejects_unknown_product_link`, `test_bridge_rejects_inactive_link`, `test_bridge_rejects_mismatched_wholesaler`, `test_bridge_rejects_cross_tenant_link`, `test_bridge_rejects_non_staff_actor`, `test_bridge_rejects_invalid_service_credentials` — all assert rejection and no job persisted.
- ✅ **Given a BFashion-originated job, when status is requested, then the initiating UI can retrieve its Virtual Closet job state**: `test_bridge_status_retrievable_by_link_owner`; `test_bridge_status_rejects_job_owned_by_another_tenant` proves isolation.
- ✅ **Product/wholesaler links are explicit and fail closed**: ownership resolved only from `ProductLink`; tenant/wholesaler mismatch paths rejected.
- ✅ **BFashion cannot invoke OpenAI directly**: the bridge reuses `ImageGenerationService` and the same Celery task; no provider credentials or second path are exposed (asserted no secrets in responses).
- ✅ **Contract tests cover accepted and rejected requests**: 11 contract tests covering both.
- ✅ **Edge case — BFashion unavailable**: job is created and persisted in Virtual Closet before enqueue (existing commit-before-enqueue); sync/retry of delivery is owned by bolt 048.

### Issues Found

None blocking. Two items are intentionally deferred:

- The BFashion-side client is implemented in a separate repository (`~/dev/bfashion/ecommerce`) and consumes the contract fixed by this bolt.
- Result/artifact download and publication to `ProductImage` belong to bolt 048 (selection + sync delivery).

### Notes

- Tests were run against a disposable PostgreSQL 16 instance via `TEST_DATABASE_URL`; all required tables are created from model metadata and the migration chain was validated separately.
- `ruff check` passes for every new/changed file; the repository has unrelated pre-existing lint findings outside this bolt's scope.
