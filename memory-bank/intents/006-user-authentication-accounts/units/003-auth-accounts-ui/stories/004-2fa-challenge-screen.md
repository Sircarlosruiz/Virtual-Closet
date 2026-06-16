---
id: 004-2fa-challenge-screen
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: implemented
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: 034-auth-accounts-ui
implemented: true
---

# Story: 004-2fa-challenge-screen

## User Story

**As a** mayorista who has configured 2FA
**I want** a 2FA challenge screen after entering my credentials
**So that** I can complete the second factor and access the platform

## Acceptance Criteria

- [ ] **Given** I have passed credentials (TOTP method), **When** I am redirected to `/auth/2fa/challenge`, **Then** I see a 6-digit OTP input field and "Enter the code from your authenticator app"
- [ ] **Given** my 2FA method is SMS, **When** I reach the challenge screen, **Then** I see "We sent a code to •••••1234" and a "Resend code" link
- [ ] **Given** I submit a valid OTP, **When** the API confirms, **Then** I am redirected to the dashboard (access + refresh tokens set as httpOnly cookies)
- [ ] **Given** I submit an invalid OTP, **When** the API rejects it, **Then** I see "Incorrect code, try again" with the input cleared
- [ ] **Given** my TOTP method is active but I want to use a backup code, **When** I click "Use backup code", **Then** I see a backup code input field instead
- [ ] **Given** I submit a valid backup code, **When** the API confirms, **Then** login succeeds and I am redirected to dashboard

## Technical Notes

- Route: `/auth/2fa/challenge`
- OTP input: auto-focus, accept 6 digits only, submit on 6th digit entry (no button press needed)
- SMS "Resend" is rate-limited (3 per 10 min) — show countdown timer if limit reached
- `challenge_token` passed in memory; redirect after successful 2FA

## Dependencies

### Requires
- 003-2fa-setup-wizard

### Enables
- 007-session-aware-routing-auth-guard

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Auto-fill from SMS (on mobile) | OTP input should support `autocomplete="one-time-code"` |
| Session challenge_token expires mid-challenge | Redirect to login with "Session expired, please log in again" |
| 5 consecutive invalid OTP attempts | Re-authentication required (back to login) |

## Out of Scope

- 2FA method switching on the challenge screen (show method info only)
