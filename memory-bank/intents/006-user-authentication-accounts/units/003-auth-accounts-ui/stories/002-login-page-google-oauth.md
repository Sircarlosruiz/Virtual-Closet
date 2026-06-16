---
id: 002-login-page-google-oauth
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 002-login-page-google-oauth

## User Story

**As a** registered mayorista
**I want** a login page that supports both email/password and Google OAuth
**So that** I can access the platform using my preferred method

## Acceptance Criteria

- [ ] **Given** I navigate to `/auth/login`, **When** the page loads, **Then** I see an email+password form and a "Continue with Google" button
- [ ] **Given** I submit valid email+password credentials, **When** the API returns a `challenge_token`, **Then** I am redirected to `/auth/2fa/challenge` (or `/auth/2fa/setup` if 2FA is not configured)
- [ ] **Given** I submit invalid credentials, **When** the API returns an error, **Then** I see "Invalid email or password" — no field-level specificity
- [ ] **Given** my account is locked, **When** login is attempted, **Then** I see "Account locked. Check your email to unlock." with no retry button
- [ ] **Given** I click "Continue with Google", **When** OAuth flow completes, **Then** NextAuth session is established and I am redirected to `/auth/2fa/challenge` or `/auth/2fa/setup`
- [ ] **Given** I am already authenticated (valid session), **When** I navigate to `/auth/login`, **Then** I am redirected to `/dashboard`

## Technical Notes

- Route: `/auth/login`
- NextAuth configured with Google provider and custom credentials provider
- Custom credentials provider calls `POST /auth/login` and returns `challenge_token`
- After credentials, NextAuth session state = `pending_2fa` (not fully authenticated)
- Fully authenticated state only after 2FA is passed

## Dependencies

### Requires
- 001-registration-email-verification-pages
- 007-session-aware-routing-auth-guard

### Enables
- 003-2fa-setup-wizard
- 004-2fa-challenge-screen

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Google OAuth popup blocked | Fallback to redirect-based flow |
| Network error during login | Show "Connection error, please try again" |

## Out of Scope

- Account unlocking UI (linked from lockout email, handled in separate email template)
