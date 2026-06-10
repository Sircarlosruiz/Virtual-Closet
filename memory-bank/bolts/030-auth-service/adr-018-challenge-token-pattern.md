---
adr: 018
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
---

# ADR-018: Challenge Token Pattern for 2-Step Authentication

## Context

The existing authentication flow issues a full JWT access token immediately after credential validation. The new auth flow requires 2FA (TOTP or SMS OTP) before issuing a JWT. This creates a need for an intermediate credential that proves the user passed the first step (email + password) without granting full access.

The platform will eventually support TOTP 2FA, SMS OTP fallback, and Google OAuth — all of which require a multi-step authentication flow.

## Decision

Implement a `challenge_token` — a short-lived (5-minute TTL) HS256-signed JWT issued after successful credential validation. The `challenge_token` encodes `user_id` and `step: "credentials_passed"`. It is NOT an access token and cannot be used to access protected routes.

The `challenge_token` must be presented to the 2FA endpoint along with the OTP code. Only after successful 2FA validation is a full JWT (access + refresh) issued.

**Token Structure**:
```json
{
  "sub": "<user_id>",
  "step": "credentials_passed",
  "iat": 1718000000,
  "exp": 1718000300
}
```

**Flow**:
1. `POST /api/auth/login` → validates credentials → returns `{ challenge_token, requires_2fa_setup }`
2. `POST /api/auth/2fa/verify` → validates OTP + challenge_token → returns `{ access_token, refresh_token }`

## Rationale

- **Security**: No JWT is issued until 2FA is completed, preventing access to protected routes without full authentication
- **Stateless**: Challenge token is self-contained (JWT), no server-side storage needed
- **Short-lived**: 5-minute TTL limits the window for replay attacks
- **Explicit step tracking**: The `step` claim makes it clear which authentication step was completed
- **Extensible**: Same pattern works for TOTP, SMS OTP, and OAuth flows

## Consequences

- **Positive**: Clear separation between credential validation and session issuance; consistent 2FA flow across all auth methods
- **Negative**: Adds complexity to the login flow; frontend must handle the intermediate state
- **Risk**: If challenge_token is leaked, attacker could attempt 2FA bypass — mitigated by short TTL and requirement of valid OTP
- **Migration**: Existing `login` endpoint must be updated to return `challenge_token` instead of `access_token`
