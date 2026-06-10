---
id: 030-auth-service
unit: 001-auth-service
intent: 006-user-authentication-accounts
type: ddd-construction-bolt
status: complete
stories:
  - 001-mayorista-registration
  - 002-email-verification
  - 003-login-email-password
  - 004-account-lockout
created: 2026-06-08T00:00:00.000Z
started: 2026-06-10T00:00:00.000Z
completed: "2026-06-10T16:16:20Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-10T00:00:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-10T00:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-10T00:00:00.000Z
    artifact: adr-018-challenge-token-pattern.md, adr-019-extend-mayorista-model.md, adr-020-backfill-existing-users-verified.md, adr-021-atomic-failed-attempts-increment.md
  - name: implement
    completed: 2026-06-10T00:00:00.000Z
    artifact: source code
  - name: test
    completed: 2026-06-10T00:00:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 028-tenant-account-service
enables_bolts:
  - 031-auth-service
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 030-auth-service

### Objective

Core user identity foundation: `User` model, mayorista registration with email verification, email+password login returning a `challenge_token`, and account lockout after 5 failed attempts.

### Stories Included

- [ ] **001-mayorista-registration**: Mayorista Registration (email+password + tenant creation) — Priority: Must
- [ ] **002-email-verification**: Email Verification (token-based, single-use) — Priority: Must
- [ ] **003-login-email-password**: Login with Email + Password → challenge_token — Priority: Must
- [ ] **004-account-lockout**: Account Lockout after 5 Failed Attempts — Priority: Must

### Expected Outputs

- `User` SQLAlchemy model (with `tenant_id` FK, `role`, `email_verified`, `is_locked`, `failed_attempts`)
- `EmailVerificationToken` model
- `POST /auth/register`, `GET /auth/verify-email`, `POST /auth/resend-verification` endpoints
- `POST /auth/login` endpoint (returns `challenge_token`, not full JWT)
- `POST /auth/unlock` endpoint
- bcrypt password hashing, timing-safe comparison
- Unit + integration tests; rate limiting on registration + resend

### Dependencies

#### Bolt Dependencies (within intent)
- **028-tenant-account-service** (Required): `Tenant` model and tenant creation logic must exist

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- 031-auth-service (2FA needs User entity and challenge_token pattern)
