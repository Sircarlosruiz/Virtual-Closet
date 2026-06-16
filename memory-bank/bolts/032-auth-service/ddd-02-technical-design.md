---
unit: 001-auth-service
bolt: 032-auth-service
stage: design
status: complete
created: 2026-06-10T00:00:00Z
---

# Technical Design - Auth Service (Password Reset + JWT Sessions)

## Architecture Pattern

**Clean Architecture / Domain-Driven Layers** — Extends the existing FastAPI + SQLAlchemy async codebase. This bolt adds password reset and JWT session management to the auth domain. The `PasswordResetToken` model is a new table; `RefreshToken` already exists from bolt 030 but needs enhanced operations (rotation, bulk revocation). RS256 key management is added to `core/security.py`.

**Rationale**: Consistent with the project's established layer structure. RS256 replaces the current HS256 for access tokens (as specified in tech-stack.md). The Redis denylist (ADR-016) is extended to cover refresh token revocation and password reset session invalidation.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  api/routers/auth_reset.py (forgot/reset)
│                             │  api/routers/auth_session.py (refresh/logout)
│                             │  api/routers/auth.py (JWKS endpoint)
│                             │  Pydantic schemas in api/schemas/
├─────────────────────────────┤
│      Application            │  services/password_reset_service.py
│                             │  services/session_service.py
│                             │  services/jwks_manager.py
│                             │  services/redis_denylist_service.py
├─────────────────────────────┤
│        Domain               │  Domain logic within services
│                             │  Domain exceptions
├─────────────────────────────┤
│     Infrastructure          │  repositories/refresh_token_repo.py (enhanced)
│                             │  repositories/password_reset_token_repo.py
│                             │  models/password_reset_token.py
│                             │  core/security.py (RS256 signing/verification)
│                             │  core/redis_client.py (denylist operations)
└─────────────────────────────┘
```

## API Design

### Password Reset

1 - **`POST /auth/forgot-password`** — Request password reset
   - **Auth**: None (public endpoint)
   - **Request**: `{ "email": "user@example.com" }`
   - **Response**: `{ "message": "If the email exists, a reset link has been sent" }` (always 200)
   - **Errors**: `429` rate limit exceeded (3 per hour per email)
   - **Behavior**: Generates token, sends email, returns identical response regardless of email existence

2 - **`POST /auth/reset-password`** — Complete password reset
   - **Auth**: None (public endpoint, token-based)
   - **Request**: `{ "token": "abc123...", "new_password": "NewPass123" }`
   - **Response**: `{ "message": "Password reset successfully" }`
   - **Errors**: `400` invalid/expired/used token, `422` password validation failure

### JWT Session Management

3 - **`POST /auth/refresh`** — Rotate refresh token
   - **Auth**: Refresh token cookie (`httpOnly`)
   - **Request**: Cookie `refresh_token=<jwt>`
   - **Response**: Sets new `access_token` and `refresh_token` cookies
   - **Errors**: `401` invalid/expired/revoked token, `503` Redis unavailable (fail closed)

4 - **`POST /auth/logout`** — Single-device logout
   - **Auth**: Refresh token cookie or access token
   - **Request**: Cookie `refresh_token=<jwt>` (optional if access token provided)
   - **Response**: `{ "message": "Logged out successfully" }`, clears cookie
   - **Errors**: `401` not authenticated

5 - **`POST /auth/logout-all`** — All-devices logout
   - **Auth**: Access token (required)
   - **Request**: `{}` (authenticated via access token)
   - **Response**: `{ "message": "Logged out from all devices", "revoked_count": N }`
   - **Errors**: `401` not authenticated

6 - **`GET /.well-known/jwks.json`** — Public JWKS endpoint
   - **Auth**: None (public endpoint)
   - **Response**: `{ "keys": [{ "kty": "RSA", "kid": "...", "n": "...", "e": "AQAB" }] }`
   - **Errors**: `500` key pair not configured

## Data Persistence

### New Table

1 - **`password_reset_tokens`**
   - Columns: `id` (UUID PK), `mayorista_id` (UUID FK → mayorista.id), `token_hash` (VARCHAR(60)), `expires_at` (TIMESTAMPTZ), `used` (BOOLEAN DEFAULT false), `used_at` (TIMESTAMPTZ, nullable), `created_at` (TIMESTAMPTZ)
   - Relationships: `mayorista_id` → `mayorista.id`, ON DELETE CASCADE
   - Indexes: INDEX(mayorista_id, used)

### Existing Table (Enhanced)

2 - **`refresh_tokens`** (from bolt 030)
   - Already has: `id`, `mayorista_id`, `jti`, `expires_at`, `revoked`, `created_at`
   - No schema changes needed. Enhanced repository operations: `revoke_all(mayorista_id)`, `get_active_by_mayorista(mayorista_id)`.

### Redis Keys

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `denylist:{jti}` | Remaining refresh token lifetime | Revoked refresh token JTIs (ADR-016) |
| `reset:rate:{email}` | 3600s | Rate limit for password reset requests (3 per hour) |

## Security Design

| Concern | Approach |
|---------|----------|
| **RS256 JWT Signing** | RSA 2048-bit key pair. Private key from `JWT_PRIVATE_KEY` env var (PEM format). Public key derived and served at JWKS endpoint. |
| **Access Token Claims** | `{ sub: user_id, tenant_id, role, iat, exp, jti }`. `tenant_id` required for all downstream tenant scoping. |
| **Refresh Token Storage** | HttpOnly cookie, `sameSite=lax`, `secure=True` in production. 7-day TTL. |
| **Token Rotation** | Each refresh issues new refresh token + new access token. Old refresh token JTI added to Redis denylist immediately. |
| **Fail Closed** | If Redis unavailable during refresh, return 503. Do not allow potentially revoked tokens. |
| **Password Reset Token** | bcrypt-hashed (cost ≥ 12), single-use, 1-hour TTL. New request invalidates all previous unused tokens. |
| **Session Revocation on Reset** | All refresh tokens revoked + JTIs added to Redis denylist. Access token remains valid until 15-min expiry (accepted risk). |
| **No Enumeration** | Forgot-password returns identical 200 response whether email exists or not. |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| **Performance** | JWT verification is pure computation (RSA signature check, < 1ms). Redis denylist check is sub-ms. All session endpoints < 50ms p95. |
| **Scalability** | Redis denylist enables horizontal scaling — any worker can check revocation. RS256 public key verification is stateless (no DB lookup for access tokens). |
| **Reliability** | Redis outage causes fail-closed (503 on refresh) — safer than allowing revoked tokens. Password reset requires email delivery — graceful degradation with console mode. |
| **Token Rotation Race** | Atomic Redis SETNX for denylist entry. First refresh succeeds; concurrent second finds JTI already in denylist → 401. |

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Invalid/expired refresh token | 401 | `{"detail": {"code": "INVALID_REFRESH_TOKEN", "message": "Session expired, please log in again"}}` |
| Revoked refresh token | 401 | `{"detail": {"code": "REVOKEN_TOKEN", "message": "Session expired, please log in again"}}` |
| Redis unavailable during refresh | 503 | `{"detail": {"code": "SERVICE_UNAVAILABLE", "message": "Session service temporarily unavailable"}}` |
| Invalid/expired password reset token | 400 | `{"detail": {"code": "INVALID_RESET_TOKEN", "message": "Link expired, please request a new one"}}` |
| Used password reset token | 400 | `{"detail": {"code": "USED_RESET_TOKEN", "message": "Link already used, please request a new one"}}` |
| Password validation failure | 422 | Standard Pydantic validation errors |
| Rate limit exceeded (reset) | 429 | `{"detail": {"code": "RESET_RATE_LIMITED", "message": "Too many reset requests. Try again later."}}` |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| **Redis** | Refresh token denylist, password reset rate limiting | `redis-py` async client. Shared with existing denylist and 2FA ephemeral state (ADR-023). |
| **Email Service** | Password reset email delivery | Resend or console mode (existing `email_service.py`). |
| **Cryptography** | RSA key pair generation, RS256 signing/verification | `cryptography` library (already added in bolt 031). |
