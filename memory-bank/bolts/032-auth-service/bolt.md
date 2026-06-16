---
id: 032-auth-service
unit: 001-auth-service
intent: 006-user-authentication-accounts
type: ddd-construction-bolt
status: complete
stories:
  - 008-password-reset
  - 009-jwt-session-management
created: 2026-06-08T00:00:00.000Z
started: 2026-06-10T00:00:00.000Z
completed: "2026-06-10T20:59:24Z"
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
    artifact: adr-026-rs256-asymmetric-signing.md, adr-027-fail-closed-redis-outage.md, adr-028-immediate-denylist-on-rotation.md, adr-029-password-reset-revokes-sessions.md
  - name: implement
    completed: 2026-06-10T00:00:00.000Z
    artifact: source code
requires_bolts:
  - 031-auth-service
enables_bolts:
  - 033-auth-accounts-ui
  - 034-auth-accounts-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 032-auth-service

### Objective

Complete the auth service with password reset and full JWT session lifecycle (RS256 access tokens, rotating refresh tokens, Redis denylist, single-device and all-devices logout).

### Stories Included

- [ ] **008-password-reset**: Password Reset via Single-Use Email Link — Priority: Must
- [ ] **009-jwt-session-management**: JWT Sessions (RS256, 15min/7day, refresh rotation, Redis denylist, logout) — Priority: Must

### Expected Outputs

- `PasswordResetToken` model
- `POST /auth/forgot-password`, `POST /auth/reset-password` endpoints
- JWT issuance after 2FA: RS256, claims `{ sub, tenant_id, role, iat, exp, jti }`
- `POST /auth/refresh` (rotation), `POST /auth/logout`, `POST /auth/logout-all` endpoints
- `GET /.well-known/jwks.json` (public key endpoint)
- Redis denylist integration for refresh token invalidation
- RS256 key pair generation documented in env setup
- Unit + integration tests; denylist race condition tests

### Dependencies

#### Bolt Dependencies (within intent)
- **031-auth-service** (Required): 2FA challenge completion triggers JWT issuance

#### Unit Dependencies (cross-unit)
- None (external: Redis must be available)

#### Enables (other bolts waiting on this)
- 033-auth-accounts-ui (needs working JWT to test session-aware routing)
- 034-auth-accounts-ui (2FA UI needs JWT issuance after challenge)
