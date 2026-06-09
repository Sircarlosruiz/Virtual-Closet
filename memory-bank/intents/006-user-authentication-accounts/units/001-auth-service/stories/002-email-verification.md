---
id: 002-email-verification
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 002-email-verification

## User Story

**As a** newly registered mayorista
**I want** to verify my email address by clicking a link
**So that** my account is activated and I can log in

## Acceptance Criteria

- [ ] **Given** I receive a verification email, **When** I click the link with a valid token, **Then** my `email_verified` flag is set to `true` and I am redirected to the login page with a success message
- [ ] **Given** I click a verification link that has expired (>24 hours), **When** the token is validated, **Then** I see an "link expired" page with a "resend verification" option
- [ ] **Given** I click a verification link that has already been used, **When** the token is validated, **Then** I see an "already verified" page redirecting to login
- [ ] **Given** I click a tampered or invalid token, **When** the token is validated, **Then** I receive a 400 error with no detail that reveals token structure
- [ ] **Given** I request a new verification email, **When** I submit my email, **Then** a new token is issued (previous token invalidated) and email is resent

## Technical Notes

- Verification endpoint: `GET /auth/verify-email?token={token}`
- Resend endpoint: `POST /auth/resend-verification`
- Token single-use: mark `used=true` on first use
- Resend rate limit: 3 requests per email per hour

## Dependencies

### Requires
- 001-mayorista-registration

### Enables
- 003-login-email-password

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User verifies twice (double-click) | Second verification is idempotent: no error, redirect to login |
| Resend before expiry | New token issued, old token invalidated |

## Out of Scope

- Google OAuth users (no email verification needed — Google already verified)
