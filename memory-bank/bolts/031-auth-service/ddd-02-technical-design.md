---
unit: 001-auth-service
bolt: 031-auth-service
stage: design
status: complete
created: 2026-06-10T00:00:00Z
---

# Technical Design - Auth Service (2FA + OAuth)

## Architecture Pattern

**Clean Architecture / Domain-Driven Layers** — Consistent with the existing backend structure (`backend/` domain-driven layers per coding standards). This bolt extends the existing FastAPI + SQLAlchemy async codebase established in bolt 030. The domain model from Stage 1 maps directly to the existing layer structure: models → repositories → services → routers.

**Rationale**: The project already uses domain-driven file organization. This bolt adds new domain concepts (2FA, OAuth) that fit naturally into the existing `models/`, `repositories/`, `services/`, `api/routers/`, `api/schemas/` structure. No new architectural patterns are introduced.

## Layer Structure

```text
┌─────────────────────────────┐
│      Presentation           │  api/routers/auth_2fa.py, api/routers/auth_oauth.py
│                             │  Pydantic schemas in api/schemas/
├─────────────────────────────┤
│      Application            │  services/two_factor_setup_service.py
│                             │  services/two_factor_challenge_service.py
│                             │  services/sms_otp_service.py
│                             │  services/oauth_exchange_service.py
├─────────────────────────────┤
│        Domain               │  Domain logic within services (no separate domain/
│                             │  folder — services contain business rules per
│                             │  existing project convention)
├─────────────────────────────┤
│     Infrastructure          │  repositories/two_factor_config_repo.py
│                             │  repositories/backup_code_repo.py
│                             │  repositories/sms_otp_repo.py
│                             │  repositories/oauth_link_repo.py
│                             │  models/two_factor.py, models/oauth.py
│                             │  External: Twilio, Redis, pyotp
└─────────────────────────────┘
```

## API Design

### 2FA Setup & Challenge

1 - **`POST /auth/2fa/setup`** — Initiate 2FA setup (TOTP or SMS)
   - **Auth**: Requires valid `challenge_token` in `Authorization: Bearer <challenge_token>` header
   - **Request**: `{ "method": "totp" | "sms", "phone_number": "+50588881234" }` (phone required only for sms)
   - **Response (totp)**: `{ "totp_secret": "JBSWY3DPEHPK3PXP...", "otpauth_uri": "otpauth://totp/...", "backup_codes": ["ABCD1234", ...] }`
   - **Response (sms)**: `{ "phone_number": "+5058888****", "otp_sent": true }`
   - **Errors**: `401` invalid/expired challenge_token, `400` invalid phone format, `409` 2FA already configured

2 - **`POST /auth/2fa/setup/confirm`** — Confirm TOTP or SMS setup
   - **Auth**: Requires valid `challenge_token`
   - **Request**: `{ "otp_code": "123456" }`
   - **Response**: `{ "configured": true, "method": "totp" | "sms", "backup_codes_remaining": 8 }`
   - **Errors**: `401` invalid challenge_token, `400` invalid OTP code, `409` already configured

3 - **`POST /auth/2fa/challenge`** — Submit TOTP/backup code during login
   - **Auth**: Requires valid `challenge_token`
   - **Request**: `{ "otp_code": "123456" }` or `{ "backup_code": "ABCD1234" }`
   - **Response**: `{ "challenge_consumed": true }` — signals to bolt 032 to issue JWT
   - **Errors**: `401` invalid challenge_token, `400` invalid code (no attempt count revealed), `429` max attempts exceeded (requires re-auth)

### SMS OTP

4 - **`POST /auth/2fa/sms/send`** — Send SMS OTP during login challenge
   - **Auth**: Requires valid `challenge_token`
   - **Request**: `{}` (phone number from TwoFactorConfig)
   - **Response**: `{ "otp_sent": true, "phone_masked": "+5058888****" }`
   - **Errors**: `401` invalid challenge_token, `409` user has no SMS 2FA configured, `429` rate limit exceeded

5 - **`POST /auth/2fa/sms/verify`** — Verify SMS OTP during login challenge
   - **Auth**: Requires valid `challenge_token`
   - **Request**: `{ "otp_code": "123456" }`
   - **Response**: `{ "challenge_consumed": true }`
   - **Errors**: `401` invalid challenge_token, `400` invalid/expired OTP, `429` max attempts exceeded

### OAuth Exchange

6 - **`POST /auth/oauth/exchange`** — Exchange NextAuth Google session for challenge_token
   - **Auth**: Requires NextAuth session token (verified server-side by NextAuth before calling FastAPI)
   - **Request**: `{ "nextauth_token": "...", "provider": "google" }`
   - **Response (new user)**: `{ "challenge_token": "...", "requires_2fa_setup": true, "requires_business_name": true }`
   - **Response (existing user, 2FA configured)**: `{ "challenge_token": "...", "requires_2fa_setup": false, "requires_2fa_challenge": true }`
   - **Response (existing email+password user, not yet linked)**: `{ "requires_account_linking": true, "email": "user@example.com" }`
   - **Errors**: `400` invalid/missing token, `409` email conflict without linking

## Data Persistence

### New Tables (Alembic migration)

1 - **`two_factor_configs`**
   - Columns: `id` (UUID PK), `user_id` (UUID FK → users.id, unique), `method` (VARCHAR(4) CHECK IN ('totp','sms')), `totp_secret_encrypted` (TEXT, nullable), `phone_number_encrypted` (TEXT, nullable), `is_configured` (BOOLEAN DEFAULT false), `backup_codes_remaining` (INTEGER DEFAULT 0), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ)
   - Relationships: `user_id` → `users.id` (one-to-one), ON DELETE CASCADE
   - Indexes: UNIQUE(user_id)

2 - **`backup_codes`**
   - Columns: `id` (UUID PK), `user_id` (UUID FK → users.id), `code_hash` (VARCHAR(60)), `used` (BOOLEAN DEFAULT false), `used_at` (TIMESTAMPTZ, nullable), `created_at` (TIMESTAMPTZ)
   - Relationships: `user_id` → `users.id`, ON DELETE CASCADE
   - Indexes: INDEX(user_id, used)

3 - **`sms_otp_records`**
   - Columns: `id` (UUID PK), `user_id` (UUID FK → users.id, unique), `otp_hash` (VARCHAR(60)), `expires_at` (TIMESTAMPTZ), `attempts` (INTEGER DEFAULT 0), `created_at` (TIMESTAMPTZ)
   - Relationships: `user_id` → `users.id`, ON DELETE CASCADE
   - Indexes: UNIQUE(user_id) — only one active OTP per user

4 - **`oauth_links`**
   - Columns: `id` (UUID PK), `user_id` (UUID FK → users.id), `provider` (VARCHAR(10) DEFAULT 'google'), `provider_sub` (VARCHAR(255)), `provider_email` (VARCHAR(255)), `linked_at` (TIMESTAMPTZ)
   - Relationships: `user_id` → `users.id`, ON DELETE CASCADE
   - Indexes: UNIQUE(provider, provider_sub), INDEX(user_id)

### Redis Keys

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `totp:used:{user_id}:{totp_code}` | 90s | Replay protection — reject duplicate TOTP codes within validity window |
| `sms:rate:{user_id}` | 600s | Rate limit counter — max 3 sends per 10-minute window |
| `sms:otp:{user_id}` | 300s | Active SMS OTP hash (alternative to DB storage for performance) |
| `challenge:consumed:{jti}` | 300s | Single-use tracking for challenge_token consumption |

## Security Design

| Concern | Approach |
|---------|----------|
| **TOTP Secret Storage** | Encrypted with Fernet (symmetric). Key from `TWO_FACTOR_ENCRYPTION_KEY` env var. Never logged, never returned after setup confirmation. |
| **Phone Number Storage** | Encrypted with Fernet (same key as TOTP secret). Masked in all API responses (`+5058888****`). |
| **Backup Code Storage** | bcrypt hashed (cost ≥ 12, per coding standards). Plaintext shown exactly once at setup. |
| **SMS OTP Storage** | bcrypt hashed in Redis with 5-min TTL. Plaintext never persisted. |
| **Challenge Token** | HS256-signed, 5-min TTL, single-use via Redis tracking. Encodes `user_id` + `step: credentials_passed`. |
| **Rate Limiting** | Redis counter for SMS sends (3 per 10 min). Account lockout from bolt 030 applies to credential validation, not 2FA. |
| **TOTP Replay Protection** | Redis key per used code with 90s TTL (covers ±1 step window). Prevents same code reuse within 30s step. |
| **No User Enumeration** | All error messages generic: "Invalid code" regardless of whether user exists or 2FA is configured. |
| **OAuth Account Linking** | Requires password confirmation to link Google identity to existing email+password account. Prevents account takeover. |

## NFR Implementation

| Requirement | Design Approach |
|-------------|-----------------|
| **Performance** | TOTP validation is pure computation (pyotp, < 1ms). SMS OTP lookup via Redis (sub-ms). Challenge token validation is JWT decode + Redis check. All endpoints < 50ms p95. |
| **Scalability** | Redis for ephemeral state (replay protection, rate limits, OTP storage) enables horizontal scaling. PostgreSQL for persistent state. Twilio API is external bottleneck — rate limits client-side. |
| **Reliability** | Twilio failures surfaced as user errors with suggestion to use backup codes. Redis failures degrade gracefully: replay protection and rate limiting skip, but core auth still functions. |
| **Clock Skew Tolerance** | pyotp ±1 step window (90 seconds total). Covers typical device clock drift. |

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Invalid/expired challenge_token | 401 | `{"detail": {"code": "INVALID_CHALLENGE_TOKEN", "message": "Authentication required"}}` |
| Invalid TOTP/SMS/backup code | 400 | `{"detail": {"code": "INVALID_OTP", "message": "Invalid code"}}` |
| 2FA already configured | 409 | `{"detail": {"code": "ALREADY_CONFIGURED", "message": "Two-factor authentication is already set up"}}` |
| SMS rate limit exceeded | 429 | `{"detail": {"code": "SMS_RATE_LIMITED", "message": "Rate limit exceeded; try again in X minutes", "retry_after": 600}}` |
| Max TOTP attempts exceeded | 429 | `{"detail": {"code": "MAX_OTP_ATTEMPTS", "message": "Too many attempts. Please log in again."}}` |
| OTP expired | 400 | `{"detail": {"code": "OTP_EXPIRED", "message": "Code expired. Request a new one."}}` |
| OAuth token invalid | 400 | `{"detail": {"code": "INVALID_OAUTH_TOKEN", "message": "Google login failed, please try again or use email/password"}}` |
| Account linking required | 409 | `{"detail": {"code": "ACCOUNT_LINKING_REQUIRED", "message": "An account exists with this email. Enter your password to link.", "email": "user@example.com"}}` |
| Twilio delivery failure | 502 | `{"detail": {"code": "SMS_DELIVERY_FAILED", "message": "SMS could not be sent. Please use a backup code."}}` |

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| **Twilio** | SMS OTP delivery | REST API via `twilio` Python SDK. `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` env vars. |
| **Redis** | Replay protection, rate limiting, OTP storage, challenge token consumption | `redis-py` async client. Shared with existing refresh token denylist. |
| **pyotp** | TOTP generation and validation | Python library. RFC 6238, SHA-1, 6-digit, 30s step. |
| **Cryptography (Fernet)** | Symmetric encryption for TOTP secrets and phone numbers | `cryptography` library. Key from `TWO_FACTOR_ENCRYPTION_KEY` env var. |
| **NextAuth** | Google OAuth session management | Frontend (Next.js). Server-side callback calls FastAPI `/auth/oauth/exchange` with session token. |
| **Google OAuth 2.0** | Identity provider | Configured via NextAuth. `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` env vars. |
