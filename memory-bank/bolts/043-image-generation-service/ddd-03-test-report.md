---
bolt: 043-image-generation-service
stage: test
created: 2026-09-17T02:00:00Z
status: blocked
---

# Test Report: Image Generation Service

## Added Coverage

- Schema validation accepts VTON try-on with garment/model/cloth inputs.
- Schema validation rejects missing mode-specific inputs.
- Non-try-on modes reject the VTON provider.
- OpenAI remains the default provider policy for non-try-on requests.

## Verification

| Command | Result |
|---|---|
| `python -m compileall -q api models repositories services tasks tests` | Passed |
| `git diff --check` | Passed |
| `pytest -q tests/test_image_generation_schema.py` | Blocked: `pydantic_settings` is not installed |
| `alembic heads` | Blocked: Alembic executable is not installed |

## Remaining Work

The worker boundary and queue contract are present, but provider execution is
deliberately deferred to bolt `044-generation-reliability`. Install the backend
dependencies and run the focused pytest file before closing this bolt.
