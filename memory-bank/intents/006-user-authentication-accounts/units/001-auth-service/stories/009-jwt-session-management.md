---
id: 009-jwt-session-management
unit: 001-auth-service
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 009-jwt-session-management

## User Story

**As a** logged-in mayorista
**I want** my session to be maintained securely with automatic token refresh
**So that** I stay logged in without re-entering credentials every 15 minutes

## Acceptance Criteria

- [ ] **Given** I complete 2FA, **When** the session is established, **Then** I receive an access token (RS256 JWT, 15-min TTL, claims: `user_id`, `tenant_id`, `role`) and a refresh token (7-day TTL, stored as `httpOnly` cookie)
- [ ] **Given** my access token is expired, **When** the frontend calls `POST /auth/refresh`, **Then** I receive a new access token and a new refresh token (rotation); the old refresh token is immediately added to the Redis denylist
- [ ] **Given** I click "Log out", **When** `POST /auth/logout` is called with the current refresh token, **Then** the token's JTI is added to the Redis denylist and the cookie is cleared
- [ ] **Given** I click "Log out from all devices", **When** `POST /auth/logout-all` is called, **Then** all `RefreshToken` records for my user are revoked and added to the denylist
- [ ] **Given** a revoked or tampered refresh token is submitted, **When** token refresh is attempted, **Then** a 401 is returned with "session expired, please log in again"
- [ ] **Given** any protected API endpoint is called, **When** the access token is validated, **Then** the JWT signature and expiry are checked; expired or invalid tokens return 401

## Technical Notes

- JWT signing: RS256 with asymmetric key pair (private key in env secret)
- Public key served at `GET /.well-known/jwks.json` for downstream services
- Refresh token denylist: Redis SET with key `denylist:{jti}`, TTL = remaining token lifetime
- Refresh endpoint: `POST /auth/refresh` — requires `refresh_token` cookie
- Logout endpoint: `POST /auth/logout`
- Logout all endpoint: `POST /auth/logout-all`
- JWT claims: `{ sub: user_id, tenant_id, role, iat, exp, jti }`

## Dependencies

### Requires
- 005-totp-2fa-setup-and-challenge (or 006) — JWT issued after 2FA

### Enables
- All platform features (all protected routes require valid JWT)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Refresh token used after logout (race condition) | Detected via denylist; 401 returned |
| Redis denylist unavailable | Fail closed — refresh returns 503 (cannot validate revocation) |
| Token rotation race (two concurrent refreshes) | First succeeds; second returns 401 (old JTI now in denylist) |

## Out of Scope

- Session management for buyer tokens (those are stateless, no server-side state)
- Admin session override (future intent)
