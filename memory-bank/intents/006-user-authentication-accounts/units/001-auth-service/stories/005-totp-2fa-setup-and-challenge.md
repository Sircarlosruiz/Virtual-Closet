---
id: 005-totp-2fa-setup-and-challenge
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 005-totp-2fa-setup-and-challenge

## User Story

**As a** mayorista logging in for the first time (or setting up 2FA)
**I want** to configure TOTP-based two-factor authentication and use it to complete login
**So that** my account is protected with a second factor

## Acceptance Criteria

- [ ] **Given** I have passed credential validation (hold a `challenge_token`), **When** I request 2FA setup, **Then** the API returns a TOTP secret and a `otpauth://` URI suitable for QR code generation; also returns 8 single-use backup codes
- [ ] **Given** I have scanned the QR code, **When** I submit a valid TOTP code to confirm setup, **Then** the `TwoFactorConfig` is saved with `is_configured=true` and backup codes are hashed and stored
- [ ] **Given** 2FA is configured, **When** I submit a valid TOTP code during the 2FA challenge, **Then** I receive an access token (15-min) and refresh token (7-day); the `challenge_token` is consumed
- [ ] **Given** I submit an incorrect TOTP code, **When** the challenge is attempted, **Then** I receive "Invalid code" without revealing remaining attempts (max 5 before re-authentication required)
- [ ] **Given** I submit a valid backup recovery code, **When** the challenge is processed, **Then** login succeeds and that backup code is marked as used (single-use)
- [ ] **Given** all backup codes are used, **When** I attempt to log in, **Then** I am prompted to regenerate backup codes after successful TOTP verification

## Technical Notes

- TOTP: RFC 6238, SHA-1, 6-digit, 30-second step, ±1 step tolerance
- TOTP secret: 32-char base32 encoded random bytes; stored encrypted in DB
- Setup endpoint: `POST /auth/2fa/setup` (requires `challenge_token`)
- Confirm setup: `POST /auth/2fa/setup/confirm` (TOTP code + `challenge_token`)
- Challenge endpoint: `POST /auth/2fa/challenge` (TOTP code + `challenge_token`)
- Backup codes: 8 × 8-char alphanumeric; hashed (bcrypt) before storage; shown plaintext once at setup
- Library: `pyotp`

## Dependencies

### Requires
- 003-login-email-password

### Enables
- 009-jwt-session-management

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Clock skew > 30s on authenticator app | ±1 step window covers 90 seconds total |
| Same TOTP code submitted twice in 30-second window | Second use rejected (replay protection) |
| `challenge_token` expired (>5 min) during setup | Re-authentication required; new login flow |

## Out of Scope

- SMS OTP fallback (story 006)
- 2FA method change (future intent)
