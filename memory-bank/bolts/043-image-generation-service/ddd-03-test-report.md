---
bolt: 043-image-generation-service
stage: test
created: 2026-09-17T05:30:49Z
status: acceptance-ready
last_verified: 2026-09-17T16:25:00Z
---

# Test Report: Image Generation Service

## Summary

- **Schema / unit tests**: 14 passed (`test_image_generation_schema.py`, `test_image_generation_task.py`)
- **API integration tests**: 6 passed (`test_image_generation_api.py`)
- **Full backend suite**: **360 passed**, 51 warnings (~245s)

## Added Coverage

- Schema validation accepts all four generation modes with required inputs.
- Schema validation rejects missing mode-specific inputs and unsupported provider/mode pairs.
- Staff-only authorization: default `mayorista` role receives HTTP 403; `staff` receives HTTP 202.
- Durable queue contract: persisted `queued` jobs and Celery dispatch with only `job_id` in task args.
- Secret boundary: public job responses expose only `job_id`, `mode`, `provider`, `status`, `created_at`; persisted `input_data` excludes API key fields.
- Worker entry point: task name, queue, `acks_late`, invalid UUID rejection, and missing OpenAI configuration fail-closed.

## Acceptance Criteria Validation

- ✅ **001-staff-provider-selection**: Provider stored on job; unsupported combinations rejected at schema layer; responses do not expose credentials.
- ✅ **002-staff-generation-jobs**: All four modes return durable job id and `queued` status; try-on accepts VTON/OpenAI inputs; non-try-on modes queue OpenAI without garment/model pair.

## Verification

| Command | Result |
|---|---|
| `make test-backend` | **360 passed** |
| `pytest tests/test_image_generation_*.py -q` (Docker, test DB) | **20 passed** |
| `git diff --check` | Passed (prior alignment) |

## Deferred to Bolt 044

Provider execution, retry/idempotency, invocation history, and usage recording remain out of scope for this bolt. The worker task intentionally raises `NotImplementedError` until reliability work lands.

## Known Boundaries

Resource tests seed a legacy signed access cookie after HTTP registration, verification, and TOTP setup; see `memory-bank/standards/backend-suite-alignment-2026-09-17.md`. This does not affect the image-generation assertions above.
