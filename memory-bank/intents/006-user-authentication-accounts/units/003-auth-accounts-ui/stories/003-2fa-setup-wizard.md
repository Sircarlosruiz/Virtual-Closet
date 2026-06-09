---
id: 003-2fa-setup-wizard
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 003-2fa-setup-wizard

## User Story

**As a** mayorista completing first-time login
**I want** a guided 2FA setup wizard
**So that** I can configure TOTP or SMS protection for my account

## Acceptance Criteria

- [ ] **Given** I have passed credentials but have no 2FA configured, **When** I am redirected to `/auth/2fa/setup`, **Then** I see a method selection screen: "Authenticator App (recommended)" or "SMS"
- [ ] **Given** I choose Authenticator App, **When** setup loads, **Then** I see a QR code (generated from the TOTP URI), the manual entry key, and a field to enter a confirmation TOTP code
- [ ] **Given** I enter a valid TOTP code to confirm setup, **When** the API confirms, **Then** I see my 8 backup codes displayed once with a copy button and a "I've saved these" checkbox before proceeding
- [ ] **Given** I choose SMS, **When** setup loads, **Then** I see a phone number input field; after entering and submitting, I receive a test OTP to confirm the number
- [ ] **Given** I confirm my phone with the correct OTP, **When** SMS setup is complete, **Then** I see backup codes (same flow as TOTP)
- [ ] **Given** setup is complete and I click "Continue", **When** the wizard finishes, **Then** I am redirected to the dashboard with a full authenticated session (access + refresh tokens issued)

## Technical Notes

- Route: `/auth/2fa/setup`
- QR code: render `otpauth://` URI using a client-side QR library (e.g., `qrcode.react`)
- Backup codes: displayed once in a monospace grid; copy-all button; never shown again
- `challenge_token` carried in memory (not URL) between steps to avoid URL sharing

## Dependencies

### Requires
- 002-login-page-google-oauth

### Enables
- 004-2fa-challenge-screen
- 007-session-aware-routing-auth-guard

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User closes tab mid-setup | `challenge_token` expires; must log in again |
| User skips backup codes acknowledgment | "I've saved these" checkbox required before proceeding |
| Invalid TOTP during setup confirmation | Error message; QR code remains visible for re-scan |

## Out of Scope

- Changing 2FA method after initial setup (future intent)
