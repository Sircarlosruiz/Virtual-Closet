---
id: 008-password-reset
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 008-password-reset

## User Story

**As a** mayorista who forgot their password
**I want** to reset my password via a secure email link
**So that** I can regain access to my account

## Acceptance Criteria

- [ ] **Given** I submit my email on the "forgot password" page, **When** the request is processed, **Then** I receive an identical response whether or not the email exists (no enumeration), and a reset email is sent if the account exists
- [ ] **Given** I click the reset link within 1 hour, **When** I submit a new valid password, **Then** my password is updated, all active refresh tokens are invalidated, and I am redirected to login
- [ ] **Given** I click a reset link older than 1 hour, **When** the token is validated, **Then** I see "Link expired, please request a new one"
- [ ] **Given** I try to use a reset link that was already used, **When** the token is validated, **Then** I see "Link already used, please request a new one"
- [ ] **Given** I submit a new password that doesn't meet complexity requirements, **When** I submit the reset form, **Then** I see specific validation errors

## Technical Notes

- Request endpoint: `POST /auth/forgot-password`
- Reset endpoint: `POST /auth/reset-password` (token + new_password)
- Token: 32-byte hex, single-use, 1-hour TTL, stored hashed in `PasswordResetToken`
- On success: iterate and revoke all `RefreshToken` records for the user + add to Redis denylist
- Rate limit: 3 reset requests per email per hour

## Dependencies

### Requires
- 001-mayorista-registration

### Enables
- 009-jwt-session-management (all sessions invalidated on reset)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Multiple reset requests before first is used | Each new request invalidates previous token |
| Google-only account (no password) | "forgot password" flow not applicable; shown link to use Google login |
| Reset during active session | Session can continue until token expires; refresh tokens revoked |

## Out of Scope

- Admin-initiated password reset (future intent)
- Forced password change on expiry (not required per NIST SP 800-63B)
