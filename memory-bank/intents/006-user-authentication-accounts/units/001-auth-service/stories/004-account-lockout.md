---
id: 004-account-lockout
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 004-account-lockout

## User Story

**As a** platform security system
**I want** to lock mayorista accounts after repeated failed login attempts
**So that** brute-force attacks are prevented

## Acceptance Criteria

- [ ] **Given** an account has 4 failed login attempts, **When** a 5th incorrect password is submitted, **Then** the account is locked (`is_locked=true`) and a lockout notification email is sent
- [ ] **Given** a locked account, **When** login is attempted with any credentials, **Then** the response is "Account locked. Check your email for unlock instructions" — regardless of credential correctness
- [ ] **Given** a locked account, **When** the user clicks the unlock link in the lockout email, **Then** `is_locked=false`, `failed_attempts=0` are reset and the user is redirected to login
- [ ] **Given** a successful login, **When** the session is established, **Then** `failed_attempts` is reset to 0
- [ ] **Given** an unlock link older than 24 hours, **When** clicked, **Then** a new unlock email must be requested

## Technical Notes

- `failed_attempts` counter stored on the `User` record; incremented atomically
- Lock email contains a signed unlock token (same pattern as email verification, 24-hour TTL)
- Unlock endpoint: `POST /auth/unlock?token={token}`
- Do not reveal `failed_attempts` count to the caller in error responses

## Dependencies

### Requires
- 003-login-email-password

### Enables
- None (security safeguard)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Concurrent login attempts increment counter past 5 | Atomic increment; account locked at exactly 5 |
| Lockout email delivery fails | Account still locked; user must contact support |
| User successfully logs in on attempt 4, then fails on attempt 1 again | Counter reset to 1 |

## Out of Scope

- IP-based rate limiting (handled at infrastructure/API gateway level)
- Admin unlock via dashboard (future intent)
