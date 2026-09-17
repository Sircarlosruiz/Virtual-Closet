---
status: in-review
date: 2026-09-17
scope: backend legacy test suite
---

# Backend suite alignment

## Approved scope

Update the complete legacy backend suite to the current API contract, retaining
production validation and authorization. Keep PostgreSQL fixtures isolated,
use valid registration credentials, verify email and complete 2FA for resource
tests, update obsolete payloads/mocks, and run `make test-backend` from a clean DB.
For verification resend, prove the original token is invalidated and exactly one
distinct new token is issued. Preserve real failure expectations rather than
skipping tests or accepting server errors.

## Changes

- Test database URL is configurable; Docker recreates `virtual_closet_test`.
- Direct DB helpers share the fixture's session factory, with cleanup in `finally`.
- Async Redis connections close on their owning test loop; tests use logical DB
  15 by default, overridable through `TEST_REDIS_URL`. CI provisions Redis.
- Email delivery uses the console backend during tests.
- Credentials-only tests use `request_login`; resource tests use `login_user`
  to verify email and run TOTP setup/confirmation/challenge.
- Resend assertions inspect the original row, require `used=True`, require one
  new unused token with distinct ID/value, reject the old token over HTTP, and
  successfully verify email with the new token.
- Tenant fixtures supply valid photo foreign keys, enum values and batch counts.
- TryOff mocks follow current repository methods and include `output_media_id`.
- Legacy generation tests simulate storage at its boundary, enumerate all shared
  models, and select a base model explicitly for base-plan generation.
- Real defects exposed by integration tests were corrected: catalog creation
  propagates the authenticated tenant; buyer links validate signatures using the
  tenant secret and list responses reconstruct the signed URL without extending
  expiration. Regression cases reject wrong signatures, expired tokens and
  malformed/missing required claims.
- CI no longer passes `--timeout`, since pytest-timeout is not installed.

## Validation

- Final `make test-backend`: **347 passed**, 51 warnings, 245.47 seconds.
- Ruff on the 13 Python files changed in this alignment: **passed**.
- `git diff --check`: **passed**.
- No skips or xfails were introduced.

## Known boundaries

The current 2FA challenge endpoint returns `challenge_consumed` but does not issue
session cookies. Resource tests complete registration, email verification,
credential login and TOTP setup/confirmation through HTTP, then seed a signed
legacy access cookie with the same helper consumed by `get_current_mayorista`.
They intentionally do not call the final challenge endpoint because its replay
state is affected by the immediate setup-confirmation TOTP, and because no cookie
issuance exists to test. These tests do not establish end-to-end session issuance
or RS256 integration. Connecting final challenge response to protected routes is
separate application work.

The full-suite blocker for bolt 043 is resolved, but its existing seven tests
cover schemas only. Staff authorization, queue durability and worker secret
boundaries still require dedicated verification before asserting that bolt's
acceptance criteria are complete. Provider execution remains deferred to 044.

Deprecation warnings remain for FastAPI startup/status constants, Redis `setex`,
and per-request HTTPX cookies.
