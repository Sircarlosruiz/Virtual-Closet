---
id: 007-google-oauth-login
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 007-google-oauth-login

## User Story

**As a** mayorista
**I want** to log in or register using my Google account
**So that** I don't need to manage a separate password

## Acceptance Criteria

- [ ] **Given** I click "Continue with Google", **When** I authorize via Google OAuth, **Then** NextAuth creates a session and calls the FastAPI `/auth/oauth/exchange` endpoint with the identity token
- [ ] **Given** the Google email matches an existing email+password account, **When** the exchange endpoint is called for the first time via Google, **Then** I am shown a prompt to link accounts (confirm by entering my password), after which Google is linked to the existing account
- [ ] **Given** the Google email does NOT match any existing account, **When** the exchange endpoint is called, **Then** a new user and tenant are created (email pre-verified) and I am prompted to enter my business name
- [ ] **Given** OAuth exchange succeeds and 2FA is NOT configured, **When** the exchange completes, **Then** a `challenge_token` is returned and I am redirected to 2FA setup
- [ ] **Given** OAuth exchange succeeds and 2FA IS configured, **When** the exchange completes, **Then** a `challenge_token` is returned and I am redirected to 2FA challenge
- [ ] **Given** Google revokes my token or returns an error, **When** the exchange is attempted, **Then** I see "Google login failed, please try again or use email/password"

## Technical Notes

- NextAuth Google provider configured in `app/api/auth/[...nextauth]/route.ts`
- FastAPI exchange endpoint: `POST /auth/oauth/exchange` — accepts NextAuth session token, returns `challenge_token`
- NextAuth session alone does NOT grant API access; internal JWT only issued after 2FA
- Google identity verified server-side by NextAuth before calling FastAPI
- New Google users: email set to `email_verified=true` automatically (Google handles verification)

## Dependencies

### Requires
- 001-mayorista-registration (tenant creation logic reused)
- 003-login-email-password (challenge_token pattern)

### Enables
- 005-totp-2fa-setup-and-challenge
- 006-sms-otp-2fa-fallback

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Google account email changes after linking | Next login creates a new account (different email = different identity) |
| Google returns unverified email | Registration rejected; must use email+password |
| NextAuth session expires before exchange | Re-initiate OAuth flow |

## Out of Scope

- Other OAuth providers (GitHub, Facebook)
- Admin invitees using Google (they can but must accept invitation first)
