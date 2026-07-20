---
unit: 001-model-pose-service
bolt: 029-model-pose-service
stage: test
status: complete
updated: 2026-07-18T05:26:38Z
---

# Test Report - Legacy ModelPhoto Backfill

## Test Summary

| Category | Passed | Failed | Skipped | Coverage |
|----------|--------|--------|---------|----------|
| Unit | 0 | 0 | 2 | N/A |
| Integration | 0 | 0 | 2 | N/A |
| Security | 0 | 0 | 0 | - |
| Performance | 0 | 0 | 1 | - |
| **Total** | **0** | **0** | **5** | **N/A** |

Automated tests were not runnable at final verification because PostgreSQL at
`localhost:5432` was stopped. The test file was added and passes Ruff validation.
The migration was manually integration-verified against PostgreSQL before the
service stopped.

## Acceptance Criteria Validation

| Story | Criteria | Status |
|-------|----------|--------|
| 004-backfill-legacy-models | Non-curated mayorista photo gets a new Model wrapper and `pose=front` | ✅ Manual integration verification |
| 004-backfill-legacy-models | Re-running is a no-op and does not create another wrapper | ✅ Manual migration rerun verification |
| 004-backfill-legacy-models | Curated photos remain untouched | ✅ Manual integration verification |
| 004-backfill-legacy-models | Orphaned rows remain untouched and are counted | ✅ Manual integration verification |

## Unit Tests

`backend/tests/test_legacy_model_backfill.py` covers:

- Legacy row selection and `model_id`/`pose='front'` linking
- Curated-row exclusion
- Orphan-row exclusion
- Wrapper ownership preservation
- Idempotent second execution

The tests use a real PostgreSQL database and invoke the Alembic revision through
an Alembic `MigrationContext`, not a mocked SQL parser.

## Integration Tests

Manual verification performed with `alembic upgrade b7c8d9e0f1a2`:

- Legacy row linked to a generated wrapper Model with `front` pose
- Curated row remained `model_id=NULL`, `pose=NULL`
- Orphan row remained `model_id=NULL`, `pose=NULL`
- Rerun selected no already-linked rows
- Migration completed with `BackfillCompleted` summary logging

## Security Tests

No HTTP surface is introduced. The migration copies `mayorista_id` from each
photo and never groups rows across owners.

## Performance Tests

Skipped. The migration uses bounded 500-row reads. A production-scale timing
test requires the deployment PostgreSQL dataset and was not run locally.

## Coverage Report

Coverage measurement is not applicable to the SQL migration itself. Acceptance
coverage is represented by the dedicated integration test scenarios and the
manual PostgreSQL verification above. Automated execution must be rerun when
the test database is available.

## Issues Found

| Issue | Severity | Status |
|-------|----------|--------|
| PostgreSQL test service stopped during final automated verification | Medium | Open / environment |
| Shared Alembic graph has an unrelated second head `d2e3f4a5b6c7` | Medium | Open / external workstream |
| Shared Alembic runner owns the migration transaction; internal per-batch commits are incompatible | Low | Fixed; design and ADR updated |

## Ready for Operations

- [x] Acceptance criteria manually validated
- [ ] Automated migration tests passing — blocked by stopped PostgreSQL
- [x] No critical/high severity implementation issues open
- [ ] Performance targets measured — no targets defined; production timing pending
- [x] Curated/orphan data protection validated
