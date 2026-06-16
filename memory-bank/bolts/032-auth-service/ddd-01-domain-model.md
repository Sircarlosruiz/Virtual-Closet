---
unit: 001-auth-service
bolt: 032-auth-service
stage: model
status: complete
created: 2026-06-10T00:00:00Z
---

# Static Model - Auth Service (Password Reset + JWT Sessions)

## Bounded Context

**Session & Password Recovery Context** — Responsible for completing the authentication chain: issuing JWT sessions after 2FA challenge completion (bolt 031), managing the refresh token lifecycle (rotation, revocation, denylist), and handling password recovery via single-use email links. This context bridges credential validation + 2FA (bolts 030, 031) with protected resource access across the platform. The Redis denylist (ADR-016) is the central revocation mechanism.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **RefreshToken** | `id` (UUID), `mayorista_id` (FK), `jti` (unique string), `expires_at` (datetime), `revoked` (bool), `created_at` | Tracks issued refresh tokens. Each refresh token has a unique JTI (JWT ID). On rotation, old token is revoked and its JTI added to Redis denylist. Only one active refresh token per device (future: multi-device support). |
| **PasswordResetToken** | `id` (UUID), `mayorista_id` (FK), `token_hash` (bcrypt), `expires_at` (datetime), `used` (bool), `used_at` (nullable), `created_at` | Single-use, 1-hour TTL. New request invalidates all previous unused tokens for the user. Hashed with bcrypt before storage. |
| **JWKSKeyPair** | `id` (UUID), `key_id` (kid, string), `public_key` (PEM), `private_key` (PEM, encrypted), `created_at`, `expires_at` (nullable), `is_active` (bool) | RS256 asymmetric key pair. Only one active key pair at a time. Public key served at `/.well-known/jwks.json`. Private key never exposed. Key rotation supported (future). |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **JWTClaims** | `sub` (user_id UUID), `tenant_id` (UUID), `role` (string), `iat` (datetime), `exp` (datetime), `jti` (UUID string) | RS256-signed. Access token TTL: 15 minutes. Claims immutable after issuance. `tenant_id` required for all downstream tenant scoping. |
| **RefreshTokenJTI** | `value` (UUID string, 128 chars max) | Globally unique identifier for each refresh token. Used as Redis denylist key. Never reused. |
| **PasswordResetTokenValue** | `token` (32-byte hex string) | Generated from `secrets.token_hex(32)`. Single-use. 1-hour TTL. Hashed with bcrypt before storage. |
| **SessionCookie** | `name` ("refresh_token"), `value` (JWT string), `httpOnly` (true), `secure` (bool), `sameSite` ("lax"), `maxAge` (7 days) | HttpOnly cookie for refresh token. Secure flag enabled in production. SameSite=lax for CSRF protection. |
| **RS256PrivateKey** | `pem` (string) | RSA 2048-bit minimum. Stored as environment secret. Never logged or transmitted. |
| **RS256PublicKey** | `pem` (string) | Derived from private key. Served at `/.well-known/jwks.json`. Safe to expose publicly. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **Session Aggregate** | `RefreshToken` (root), `RedisDenylist` (external reference) | 1. Each refresh token has a unique JTI. 2. When a refresh token is rotated, the old JTI is immediately added to Redis denylist with TTL = remaining lifetime. 3. A revoked token cannot be un-revoked. 4. If Redis denylist is unavailable, refresh operations fail closed (503). 5. Concurrent refresh attempts: first succeeds, second fails (old JTI now in denylist). |
| **PasswordReset Aggregate** | `PasswordResetToken` (root), `Mayorista` (external reference) | 1. Only one active reset token per user at a time (new request invalidates previous). 2. Token is single-use: once consumed, cannot be reused. 3. Token expires after 1 hour. 4. On successful password reset, ALL refresh tokens for the user are revoked. 5. Response is identical whether email exists or not (no enumeration). |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **SessionIssued** | 2FA challenge completed successfully | `user_id`, `tenant_id`, `role`, `jti`, `access_token_expires_at`, `refresh_token_expires_at` |
| **SessionRefreshed** | Valid refresh token submitted to `/auth/refresh` | `user_id`, `old_jti`, `new_jti`, `new_access_token_expires_at` |
| **SessionRevoked** | User logs out (single device) | `user_id`, `jti`, `reason` (user_logout) |
| **AllSessionsRevoked** | User logs out from all devices | `user_id`, `revoked_count` (int) |
| **PasswordResetRequested** | User submits email on forgot password page | `user_id` (if exists), `token_expires_at` |
| **PasswordResetCompleted** | User submits valid token + new password | `user_id`, `tokens_revoked_count` (int) |
| **PasswordResetTokenInvalidated** | New reset request issued before previous was used | `user_id`, `invalidated_token_id` (UUID) |
| **DenylistEntryCreated** | Refresh token JTI added to Redis denylist | `jti`, `ttl_seconds`, `reason` (rotation\|logout\|password_reset) |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **SessionService** | `issue_session(user_id, tenant_id, role)` → access_token + refresh_token; `refresh_session(refresh_token)` → new access_token + new refresh_token (rotate); `revoke_session(jti)` → add to denylist; `revoke_all_sessions(user_id)` → revoke all + denylist; `validate_access_token(token)` → claims or None | `JWKSManager`, `RefreshTokenRepo`, `RedisDenylistService`, `MayoristaRepo`, `TenantRepo` |
| **PasswordResetService** | `request_reset(email)` → token or silent success; `complete_reset(token, new_password)` → update password + revoke sessions; `validate_token(token)` → valid/invalid/expired/used | `PasswordResetTokenRepo`, `MayoristaRepo`, `SessionService`, `EmailService` |
| **JWKSManager** | `get_active_key_pair()` → (private_key, public_key, kid); `get_public_keys()` → list of active public keys for JWKS endpoint; `generate_key_pair()` → new JWKSKeyPair | `cryptography` library, `JWKSKeyPairRepo` (optional, or env-based) |
| **RedisDenylistService** | `add(jti, ttl_seconds)` → add to denylist; `is_denied(jti)` → bool; `check_and_fail_closed(jti)` → bool (raises if Redis unavailable) | `redis-py`, ADR-016 |

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **RefreshTokenRepo** | `RefreshToken` | `create(mayorista_id, jti, expires_at)` → RefreshToken; `get_by_jti(jti)` → RefreshToken\|None; `get_active_by_mayorista(mayorista_id)` → list[RefreshToken]; `revoke(jti)` → None; `revoke_all(mayorista_id)` → list[RefreshToken] |
| **PasswordResetTokenRepo** | `PasswordResetToken` | `create(mayorista_id, token_hash, expires_at)` → PasswordResetToken; `find_by_token_hash(token_hash)` → PasswordResetToken\|None; `invalidate_all_unused(mayorista_id)` → None; `mark_used(token)` → None |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Access Token** | Short-lived (15-min) RS256 JWT granting API access. Contains `sub`, `tenant_id`, `role`, `jti`, `iat`, `exp`. |
| **Refresh Token** | Long-lived (7-day) opaque token stored in HttpOnly cookie. Used to obtain new access tokens. Rotated on each use. |
| **Token Rotation** | Pattern where each refresh token use issues a new refresh token and revokes the old one. Prevents token replay. |
| **JTI** | JWT ID — unique identifier for each JWT. Used as the key in the Redis denylist for revocation tracking. |
| **Redis Denylist** | Redis SET storing revoked JTIs with TTL matching remaining token lifetime. Checked on every refresh (ADR-016). |
| **Fail Closed** | When Redis denylist is unavailable, refresh operations return 503 instead of allowing potentially revoked tokens. |
| **Password Reset Token** | Single-use, 1-hour TTL token sent via email link. Hashed with bcrypt. Revokes all sessions on use. |
| **No Enumeration** | API responses for forgot-password and login are identical whether the email exists or not. Prevents user discovery. |
| **JWKS** | JSON Web Key Set — standard format for publishing public keys. Served at `/.well-known/jwks.json`. |
| **Mayorista** | Wholesale buyer user type; the primary user role. JWT `sub` claim contains the mayorista UUID. |
