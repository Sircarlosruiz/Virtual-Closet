---
id: 001-mayorista-registration
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 001-mayorista-registration

## User Story

**As a** wholesale vendor (mayorista)
**I want** to create an account with my business email and password
**So that** I can access the Virtual Closet platform

## Acceptance Criteria

- [ ] **Given** I submit a valid email, password (≥8 chars, ≥1 uppercase, ≥1 number), and business name, **When** the registration request is processed, **Then** a new user record and tenant are created with `email_verified=false` and a verification email is sent
- [ ] **Given** I submit an email already registered, **When** I attempt to register, **Then** the API returns a generic error without revealing the account exists (no user enumeration)
- [ ] **Given** I submit a password shorter than 8 characters or without required complexity, **When** I submit, **Then** I receive a specific validation error listing unmet criteria
- [ ] **Given** registration succeeds, **When** I try to log in before verifying my email, **Then** login is rejected with a "verify your email first" message
- [ ] **Given** registration, **When** the account is created, **Then** a corresponding `Tenant` record is created and `user.tenant_id` is set

## Technical Notes

- Password hashed with bcrypt cost ≥ 12 before storage
- Verification token: 32-byte random hex, stored in `EmailVerificationToken`, expires in 24 hours
- Tenant created atomically with the user in the same DB transaction
- Registration endpoint: `POST /auth/register`
- Rate limit: 5 registration attempts per IP per 15 minutes

## Dependencies

### Requires
- `002-tenant-account-service` Story 001 (Tenant model must exist)

### Enables
- 002-email-verification
- 003-login-email-password

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Duplicate email with different casing | Normalized to lowercase; treated as duplicate |
| DB transaction fails mid-creation | Full rollback; no partial user or tenant created |
| Email service unavailable | User created; verification email queued/retried; user informed to check spam |

## Out of Scope

- Google OAuth registration (story 007)
- Admin sub-role registration (tenant-account-service story 006)
