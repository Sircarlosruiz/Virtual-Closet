---
stage: design
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
---

## Technical Design: 001-auth-service

### Architecture Pattern

**Pattern**: Layered Architecture with DDD-lite (Domain-Driven Design adapted to existing FastAPI structure)

**Rationale**: The existing backend already follows a layered pattern (routers → services → repositories → models). This bolt extends that pattern with DDD principles:
- Aggregate boundaries respected (User aggregate includes EmailVerificationToken, UnlockToken)
- Domain services encapsulate business rules
- Repository interfaces abstract data access
- Domain exceptions translated to HTTP in routers

**Decision**: Evolve the existing `Mayorista` model rather than creating a new `User` model. The `Mayorista` table already has `tenant_id`, `role`, and `password_hash`. We will add `email_verified`, `is_locked`, and `failed_attempts` columns. This avoids a disruptive migration and preserves existing relationships.

### Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│      Presentation (api/routers/auth.py)                     │  HTTP endpoints, cookies, status codes
├─────────────────────────────────────────────────────────────┤
│      API Contracts (api/schemas/auth.py)                    │  Pydantic request/response models
├─────────────────────────────────────────────────────────────┤
│      Application/Domain (services/auth_service.py)          │  Registration, login, verification, lockout
├─────────────────────────────────────────────────────────────┤
│      Data Access (repositories/mayorista_repo.py)           │  AsyncSession queries, atomic operations
├─────────────────────────────────────────────────────────────┤
│      Domain Models (models/mayorista.py, new token models)  │  SQLAlchemy entities
├─────────────────────────────────────────────────────────────┤
│      Infrastructure (core/security.py, core/limiter.py)     │  JWT, bcrypt, rate limiting, email
└─────────────────────────────────────────────────────────────┘
```

### API Design

#### Endpoints

1. **POST /api/auth/register** — Mayorista Registration
   - **Request**: `{ email: string, password: string, business_name: string }`
   - **Response (201)**: `{ id: UUID, email: string, business_name: string }`
   - **Errors**: 409 (email exists), 422 (validation), 429 (rate limit)
   - **Rate Limit**: 5 requests per IP per 15 minutes

2. **GET /api/auth/verify-email** — Email Verification
   - **Query Params**: `token: string`
   - **Response (200)**: `{ message: "Email verified successfully" }`
   - **Errors**: 400 (invalid/expired/used token), 404 (token not found)

3. **POST /api/auth/resend-verification** — Resend Verification Email
   - **Request**: `{ email: string }`
   - **Response (200)**: `{ message: "Verification email sent" }`
   - **Errors**: 404 (email not found), 429 (rate limit: 3 per email per hour)
   - **Note**: Returns generic success even if email not found (no enumeration)

4. **POST /api/auth/login** — Login with Email + Password
   - **Request**: `{ email: string, password: string }`
   - **Response (200)**: `{ challenge_token: string, requires_2fa_setup: boolean }`
   - **Errors**: 401 (invalid credentials), 403 (email not verified), 423 (account locked), 429 (rate limit)
   - **Rate Limit**: 10 requests per IP per minute (existing)

5. **POST /api/auth/unlock** — Account Unlock
   - **Query Params**: `token: string`
   - **Response (200)**: `{ message: "Account unlocked successfully" }`
   - **Errors**: 400 (invalid/expired/used token), 404 (token not found)

### Data Model

#### Schema Changes (Alembic Migration)

**Mayorista Table** (alter existing):
- ADD `email_verified` BOOLEAN NOT NULL DEFAULT FALSE
- ADD `is_locked` BOOLEAN NOT NULL DEFAULT FALSE
- ADD `failed_attempts` INTEGER NOT NULL DEFAULT 0
- ADD `updated_at` TIMESTAMP WITH TIME ZONE (for audit trail)

**New Table: email_verification_tokens**
- `id` UUID PRIMARY KEY (default uuid_generate_v4)
- `token` VARCHAR(64) UNIQUE NOT NULL (32-byte hex)
- `user_id` UUID NOT NULL REFERENCES mayorista(id) ON DELETE CASCADE
- `expires_at` TIMESTAMP WITH TIME ZONE NOT NULL
- `used` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
- Index: `idx_email_verification_token` ON `token`
- Index: `idx_email_verification_user` ON `user_id` WHERE `used = false`

**New Table: unlock_tokens**
- `id` UUID PRIMARY KEY (default uuid_generate_v4)
- `token` VARCHAR(64) UNIQUE NOT NULL (signed token)
- `user_id` UUID NOT NULL REFERENCES mayorista(id) ON DELETE CASCADE
- `expires_at` TIMESTAMP WITH TIME ZONE NOT NULL
- `used` BOOLEAN NOT NULL DEFAULT FALSE
- `created_at` TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
- Index: `idx_unlock_token` ON `token`
- Index: `idx_unlock_user` ON `user_id` WHERE `used = false`

### Security Design

#### Password Handling
- **Hashing**: bcrypt with cost factor 12 (existing `core/security.py`)
- **Comparison**: timing-safe `bcrypt.checkpw` (existing)
- **Validation**: ≥8 chars, ≥1 uppercase, ≥1 number (new Pydantic validator)

#### Challenge Token
- **Format**: HS256 JWT with 5-minute TTL
- **Payload**: `{ sub: user_id, step: "credentials_passed", iat, exp }`
- **Purpose**: Proves credentials validated; required to proceed to 2FA
- **Not an access token**: Cannot be used to access protected routes

#### Account Lockout
- **Threshold**: 5 consecutive failed login attempts
- **Counter**: Atomic increment via SQLAlchemy `UPDATE ... SET failed_attempts = failed_attempts + 1`
- **Lock trigger**: When `failed_attempts >= 5`, set `is_locked = true`
- **Unlock**: Single-use token sent via email, 24-hour TTL
- **Reset**: `failed_attempts = 0` on successful login or unlock

#### Email Verification
- **Token**: 32-byte random hex (secrets.token_hex(32))
- **TTL**: 24 hours
- **Single-use**: `used` flag set on first verification
- **Invalidation**: New token invalidates previous (set `used = true` on all existing)

#### No User Enumeration
- Registration: Returns 409 only if email already exists (acceptable for registration)
- Login: Generic "Invalid credentials" for both wrong email and wrong password
- Resend verification: Returns 200 even if email not found
- Lockout: Generic message regardless of whether account exists

### NFR Implementation

#### Performance
- **Login + credential check**: < 200ms (p95) — single DB query + bcrypt verification
- **Email verification**: < 100ms (p95) — single DB query + update
- **Registration**: < 500ms (p95) — includes tenant creation + email send (async)

#### Rate Limiting
- Registration: 5 per IP per 15 minutes (slowapi decorator)
- Login: 10 per IP per minute (existing)
- Resend verification: 3 per email per hour (slowapi decorator)

#### Reliability
- Registration + tenant creation: Atomic transaction (rollback on failure)
- Email verification: Idempotent (double-click returns success)
- Unlock: Idempotent (double-click returns success)

### Integration Points

| Integration | Type | Purpose |
|-------------|------|---------|
| `Tenant` model | Internal DB | Tenant created atomically with user |
| `core/security.py` | Internal module | bcrypt hashing, challenge_token generation |
| `core/limiter.py` | Internal module | Rate limiting (slowapi) |
| Email service | External (async) | Verification and unlock emails |
| `core/logger.py` | Internal module | Auth event logging |

### Migration Strategy

1. Create Alembic migration adding columns to `mayorista` table
2. Create Alembic migration for `email_verification_tokens` table
3. Create Alembic migration for `unlock_tokens` table
4. Backfill: Set `email_verified = true` for all existing mayoristas (they registered before this feature)
5. Set `failed_attempts = 0` and `is_locked = false` for all existing mayoristas
