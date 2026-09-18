---
stage: test
bolt: 049-openai-generation-ui
created: 2026-09-18T17:02:00Z
---

## Test Report: 004-openai-generation-ui

### Summary

- **Tests**: 29/29 passed (Vitest)
- **Coverage**: not collected
- **Backend pytest**: not executed (Postgres on :5432 is `ecommerce-db`; default `postgres:postgres` is rejected)
- **Playwright**: written, not executed (backend port 8000 is occupied by BFashion ecommerce)

### Test Files

- [x] `frontend/lib/staff-generation/validate-generation-form.test.ts` - Mode-required inputs, OpenAI-only modes, BFashion query preservation
- [x] `frontend/components/staff-generation/StaffGate.test.tsx` - Mayorista sees no generation controls; staff does
- [x] `frontend/components/staff-generation/GenerationModeForm.test.tsx` - Try-on fields by default; invalid submit does not create a job; text mode hides provider swap
- [x] `frontend/components/staff-generation/JobReviewPanel.test.tsx` - Failed jobs show error + retry; completed jobs do not
- [x] `frontend/components/staff-generation/PublicationGallery.test.tsx` - No link message; selected/discarded badges; independent destination status; retry only on failed retryable row
- [x] `backend/tests/test_product_link_lookup.py` - Role on `/me`, staff lookup, non-staff 403, unknown 404, cross-tenant fail-closed
- [x] `frontend/e2e/staff-generation.spec.ts` - Unauthenticated redirect; mayorista unauthorized page without generation chrome

### Acceptance Criteria Validation

- ✅ **Staff can pick a mode and only see that mode’s required/optional inputs and allowed providers**: `GenerationModeForm.test.tsx` (try_on fields + provider; text mode hides provider and shows OpenAI-only copy)
- ✅ **Invalid or missing input explains the issue and does not create a job**: form submit blocked; `validateGenerationForm` covers all four modes
- ✅ **BFashion deep link keeps product context through navigation**: `staffGenerationHref` keeps query string on the job route
- ✅ **Queued/processing vs completed/failed review**: `JobReviewPanel` retry/error for failed; completed hides retry
- ⏳ **SKU recomposition keeps the original listed**: covered by implementation; no dedicated component test (compose API is backend 046)
- ✅ **Failed jobs show a reason and explicit retry**: `JobReviewPanel.test.tsx`
- ✅ **Candidates distinguish undecided/selected/discarded; publish is not automatic**: gallery badges; missing `product_link_id` does not fetch or publish
- ✅ **Partial sync shows destinations independently with retry on the failed retryable one**: one retry button for BFashion failed; Virtual Closet synced
- ✅ **Retrying delivery does not imply a second gallery item**: gallery keys by candidate; retry reuses publication id (asserted by single retry control + existing backend 048 tests)
- ✅ **Non-staff users have no generation nav, form, or private draft/config**: `StaffGate` + e2e spec (e2e not run in this environment)
- ✅ **Provider, overlay-fit, and sync errors are readable**: provider error_code in review panel; gallery shows `last_error`

### Issues Found

- Local Postgres on port 5432 belongs to BFashion ecommerce, so cookie lookup tests could not run here (same constraint noted in bolt 048).
- Playwright webServer expects Virtual Closet API on `:8000`, which is currently the ecommerce API.

### Notes

- Vitest 2.1.9 and Testing Library were added as frontend devDependencies (`pnpm test`).
- Re-run backend tests with `TEST_DATABASE_URL` pointed at a Virtual Closet test database.
- Re-run `pnpm e2e e2e/staff-generation.spec.ts` when VC frontend and API are free on the configured ports.
