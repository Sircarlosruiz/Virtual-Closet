---
id: 031-auth-service
unit: 001-auth-service
intent: 006-user-authentication-accounts
type: ddd-construction-bolt
status: complete
stories:
  - 005-totp-2fa-setup-and-challenge
  - 006-sms-otp-2fa-fallback
  - 007-google-oauth-login
created: 2026-06-08T00:00:00.000Z
started: 2026-06-10T00:00:00.000Z
completed: "2026-06-10T20:08:40Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-10T00:00:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-10T00:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-10T00:00:00.000Z
    artifact: adr-022-fernet-symmetric-encryption.md, adr-023-redis-ephemeral-auth-state.md, adr-024-oauth-account-linking-security.md, adr-025-challenge-token-single-use.md
  - name: implement
    completed: 2026-06-10T00:00:00.000Z
    artifact: source code
requires_bolts:
  - 030-auth-service
enables_bolts:
  - 032-auth-service
  - 033-auth-accounts-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 2
---

## Bolt: 031-auth-service

### Objective

Implement all second-factor authentication: TOTP setup/challenge (with backup codes), SMS OTP fallback, and Google OAuth via NextAuth session exchange. All paths produce a `challenge_token` verified by 2FA before JWT issuance.

### Stories Included

- [ ] **005-totp-2fa-setup-and-challenge**: TOTP 2FA Setup (QR + secret + backup codes) + Challenge — Priority: Must
- [ ] **006-sms-otp-2fa-fallback**: SMS OTP 2FA Fallback (Twilio, rate-limited) — Priority: Must
- [ ] **007-google-oauth-login**: Google OAuth via NextAuth → challenge_token — Priority: Must

### Expected Outputs

- `TwoFactorConfig` model (TOTP secret encrypted, phone, backup codes hashed)
- `POST /auth/2fa/setup`, `POST /auth/2fa/setup/confirm`, `POST /auth/2fa/challenge` endpoints
- `POST /auth/2fa/sms/send`, `POST /auth/2fa/sms/verify` endpoints
- `POST /auth/oauth/exchange` endpoint (NextAuth session → challenge_token)
- `pyotp` TOTP integration, Twilio SMS integration
- TOTP replay protection (used-code tracking in Redis)
- Unit + integration tests for all 2FA paths

### Dependencies

#### Bolt Dependencies (within intent)
- **030-auth-service** (Required): `User` model + `challenge_token` pattern must exist

#### Unit Dependencies (cross-unit)
- None (external: Twilio, Google OAuth credentials must be provisioned)

#### Enables (other bolts waiting on this)
- 032-auth-service (JWT session management completes auth chain)
- 033-auth-accounts-ui (login + 2FA pages need all auth endpoints)
