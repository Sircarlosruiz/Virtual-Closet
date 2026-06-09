---
id: 003-login-email-password
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 003-login-email-password

## User Story

**As a** verified mayorista
**I want** to log in with my email and password
**So that** I can access the platform (pending 2FA completion)

## Acceptance Criteria

- [ ] **Given** valid credentials for a verified account with 2FA configured, **When** I submit login, **Then** I receive a short-lived `challenge_token` (5-min TTL) and am redirected to the 2FA challenge screen
- [ ] **Given** valid credentials for a verified account with 2FA NOT yet configured, **When** I submit login, **Then** I receive a `challenge_token` and am redirected to the 2FA setup wizard
- [ ] **Given** invalid credentials, **When** I submit login, **Then** I receive a generic "Invalid credentials" error (no indication of which field is wrong)
- [ ] **Given** an unverified account, **When** I submit valid credentials, **Then** login is rejected with "verify your email first" and a resend link
- [ ] **Given** a locked account, **When** I submit any credentials, **Then** login is rejected with "account locked" and instructions to unlock via email

## Technical Notes

- Login endpoint: `POST /auth/login`
- Returns `{ challenge_token, requires_2fa_setup: bool }` — NOT an access JWT
- `challenge_token` is a short-lived signed token (HS256) encoding `user_id` and `step: credentials_passed`
- Full JWT (access + refresh) is issued only after 2FA completion (story 005 or 006)
- Timing-safe comparison for password verification to prevent timing attacks

## Dependencies

### Requires
- 001-mayorista-registration
- 002-email-verification

### Enables
- 004-account-lockout
- 005-totp-2fa-setup
- 006-sms-otp-2fa-fallback

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Login with uppercase email | Normalized to lowercase before lookup |
| SQL/NoSQL injection in email field | Sanitized by ORM; login fails normally |
| Login with correct email, no account | Same generic error as wrong password |

## Out of Scope

- Google OAuth login (story 007)
- Actual JWT issuance (happens in 2FA stories)
