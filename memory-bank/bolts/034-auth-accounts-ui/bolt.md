---
id: 034-auth-accounts-ui
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
type: simple-construction-bolt
status: complete
stories:
  - 003-2fa-setup-wizard
  - 004-2fa-challenge-screen
created: 2026-06-08T00:00:00Z
started: 2026-06-12T00:00:00Z
completed: 2026-06-12T00:00:00Z
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-12T00:00:00Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-12T00:00:00Z
    artifact: source code
  - name: test
    completed: 2026-06-12T00:00:00Z
    artifact: e2e/2fa.spec.ts

requires_bolts: [033-auth-accounts-ui, 031-auth-service]
enables_bolts: [035-auth-accounts-ui]
requires_units: []
blocks: true

complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 034-auth-accounts-ui

### Objective

Implement the 2FA setup wizard (TOTP QR code + SMS phone setup + backup codes display) and the 2FA challenge screen (TOTP input or SMS OTP input with fallback to backup codes).

### Stories Included

- [ ] **003-2fa-setup-wizard**: 2FA Method Selection + TOTP QR Setup + SMS Setup + Backup Codes Display — Priority: Must
- [ ] **004-2fa-challenge-screen**: 2FA OTP Input (TOTP or SMS) + Backup Code Fallback — Priority: Must

### Expected Outputs

- `/auth/2fa/setup` page (method selector → TOTP QR or SMS phone setup → backup codes)
- `/auth/2fa/challenge` page (OTP input with TOTP/SMS toggle + backup code option)
- QR code rendering via `qrcode.react`
- SMS resend with countdown timer
- Backup codes: monospace grid, copy-all button, acknowledgment checkbox
- `challenge_token` carried in memory (not URL) between wizard steps

### Dependencies

#### Bolt Dependencies (within intent)
- **033-auth-accounts-ui** (Required): Auth infrastructure (NextAuth, cookies, guard) must exist
- **031-auth-service** (Required): 2FA setup + challenge API endpoints must exist

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- 035-auth-accounts-ui (account settings builds on full auth flow being complete)
