---
unit: 001-auth-service
bolt: 031-auth-service
stage: model
status: complete
created: 2026-06-10T00:00:00Z
---

# Static Model - Auth Service (2FA + OAuth)

## Bounded Context

**Authentication & Second-Factor Context** — Responsible for all second-factor authentication flows (TOTP, SMS OTP) and external identity exchange (Google OAuth via NextAuth). This context operates after credential validation (bolt 030) and before JWT session issuance (bolt 032). The `challenge_token` pattern (ADR-018) is the boundary contract: every entry point requires a valid challenge_token and every successful 2FA/OAuth path consumes it to authorize JWT issuance.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| **TwoFactorConfig** | `id` (UUID), `user_id` (FK), `method` (totp\|sms), `totp_secret` (encrypted base32, nullable), `phone_number` (encrypted, nullable), `is_configured` (bool), `backup_codes_remaining` (int), `created_at`, `updated_at` | One per user. Method is exclusive (totp OR sms, not both simultaneously). Cannot be changed after setup (future intent). `is_configured=true` only after successful confirmation. |
| **BackupCode** | `id` (UUID), `user_id` (FK), `code_hash` (bcrypt), `used` (bool), `used_at` (nullable), `created_at` | 8 codes generated at 2FA setup. Single-use only. Hashed with bcrypt before storage. Shown plaintext exactly once at setup. When all 8 used, user must regenerate after next successful TOTP login. |
| **SmsOtpRecord** | `id` (UUID), `user_id` (FK), `otp_hash` (bcrypt), `expires_at`, `attempts` (int), `created_at` | One active OTP per user at a time. 5-minute TTL. Max 3 attempts per OTP. Sending new OTP invalidates previous. Rate-limited: max 3 sends per 10-minute window per user. |
| **OAuthLink** | `id` (UUID), `user_id` (FK), `provider` (google), `provider_sub` (Google subject ID), `provider_email` (string), `linked_at` | Links external OAuth identity to internal user. One Google link per user. `provider_email` may differ from user's primary email if account linking occurred. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| **TotpSecret** | `value` (32-char base32 string) | Generated from 20 random bytes via `secrets.token_bytes`. Encrypted with Fernet before persistence. Never logged or exposed after setup confirmation. |
| **PhoneNumber** | `e164` (string) | Must be valid E.164 format. Validated before SMS is sent. Encrypted with Fernet before persistence. |
| **OtpCode** | `code` (6-digit integer) | Generated via `secrets.randbelow(10**6)`. Range 000000–999999. Never reused within active window. |
| **ChallengeTokenPayload** | `user_id` (UUID), `step` ("credentials_passed"), `exp` (datetime), `jti` (UUID) | HS256-signed, 5-minute TTL (ADR-018). Encoded `step` prevents direct JWT issuance. Consumed (single-use) on successful 2FA or OAuth exchange completion. |
| **BackupCodeHash** | `hash` (string) | bcrypt hash of 8-char alphanumeric code. Cost ≥ 12. Verified via `bcrypt.checkpw`. |
| **TwoFactorMethod** | `value` (enum: totp, sms) | Immutable after configuration. Determines which challenge flow is active. |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| **TwoFactorConfig Aggregate** | `TwoFactorConfig` (root), `BackupCode[]` (children) | 1. Exactly one `TwoFactorConfig` per user. 2. When `is_configured=true`, exactly 8 `BackupCode` records exist (some may be `used=true`). 3. `totp_secret` is non-null iff `method=totp`. 4. `phone_number` is non-null iff `method=sms`. 5. Backup codes cannot be regenerated without successful TOTP verification first. |
| **User Aggregate** (from bolt 030) | `User` (root), `TwoFactorConfig` (child reference), `OAuthLink[]` (children) | 1. No JWT issued until 2FA challenge succeeds (ADR-018). 2. User with `is_locked=true` cannot proceed past credential validation. 3. Google OAuth link `provider_email` must be verified (Google guarantees). 4. Account linking requires password confirmation for existing email+password users. |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| **TwoFactorSetupRequested** | User requests 2FA setup with valid `challenge_token` | `user_id`, `method` (totp\|sms), `challenge_token_jti` |
| **TwoFactorSetupCompleted** | User confirms TOTP code or SMS OTP during setup | `user_id`, `method`, `backup_codes_count` (8) |
| **TwoFactorChallengeSucceeded** | User submits valid TOTP/SMS/backup code during login challenge | `user_id`, `method`, `challenge_token_jti`, `used_backup_code` (bool) |
| **TwoFactorChallengeFailed** | User submits invalid TOTP/SMS/backup code | `user_id`, `method`, `reason` (invalid_code\|expired\|already_used\|max_attempts) |
| **SmsOtpSent** | SMS OTP dispatched via Twilio | `user_id`, `phone_number` (masked), `expires_at` |
| **SmsOtpRateLimited** | User exceeds 3 SMS sends in 10-minute window | `user_id`, `retry_after` (datetime) |
| **BackupCodeConsumed** | Valid backup code used during challenge | `user_id`, `remaining_codes` (int) |
| **BackupCodesExhausted** | All 8 backup codes used | `user_id`, `requires_regeneration` (true) |
| **OAuthAccountCreated** | New user created via Google OAuth exchange | `user_id`, `provider_sub`, `email`, `tenant_id` |
| **OAuthAccountLinked** | Google identity linked to existing email+password account | `user_id`, `provider_sub`, `previous_method` (email_password) |
| **OAuthExchangeFailed** | Google OAuth exchange fails | `email`, `reason` (no_account\|link_rejected\|token_invalid) |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| **TwoFactorSetupService** | `initiate_totp_setup(user_id)` → TOTP secret + otpauth URI + backup codes; `confirm_totp_setup(user_id, totp_code)` → saves config; `initiate_sms_setup(user_id, phone)` → sends confirmation OTP; `confirm_sms_setup(user_id, otp_code)` → saves config | `pyotp`, `secrets`, `TwoFactorConfigRepo`, `BackupCodeRepo`, `SmsProvider` |
| **TwoFactorChallengeService** | `validate_totp(user_id, totp_code)` → success/fail with replay protection; `validate_sms_otp(user_id, otp_code)` → success/fail; `validate_backup_code(user_id, code)` → success/fail + consume; `consume_challenge_token(token)` → marks consumed | `ChallengeTokenService`, `TwoFactorConfigRepo`, `SmsOtpRepo`, `BackupCodeRepo`, `Redis` (replay protection) |
| **SmsOtpService** | `send_otp(user_id, phone)` → generates + stores hashed OTP + sends via Twilio; `verify_otp(user_id, otp_code)` → validates + deletes; `check_rate_limit(user_id)` → allows/blocks | `Twilio API`, `SmsOtpRepo`, `Redis` (rate limiting), `PhoneNumber` VO |
| **OAuthExchangeService** | `exchange(nextauth_session)` → validates Google identity, creates/links user, returns `challenge_token`; `link_account(user_id, password, provider_sub)` → confirms account linking; `create_oauth_user(email, provider_sub, business_name)` → creates user + tenant | `NextAuth session`, `UserRepo`, `OAuthLinkRepo`, `ChallengeTokenService`, `TenantService` (from bolt 029) |
| **ChallengeTokenService** | `issue(user_id)` → creates HS256 challenge_token; `validate(token)` → verifies signature + expiry + single-use; `consume(token)` → marks as consumed | `python-jose` (HS256), `Redis` (single-use tracking), ADR-018 |

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| **TwoFactorConfigRepo** | `TwoFactorConfig` | `get_by_user_id(user_id)` → TwoFactorConfig\|None; `create(config)` → TwoFactorConfig; `update(config)` → None; `mark_configured(user_id, method)` → None |
| **BackupCodeRepo** | `BackupCode` | `create_batch(user_id, codes: list[BackupCodeHash])` → None; `verify_and_consume(user_id, code_plain)` → bool; `count_remaining(user_id)` → int; `get_all_unused(user_id)` → list[BackupCode] |
| **SmsOtpRepo** | `SmsOtpRecord` | `create(user_id, otp_hash, expires_at)` → SmsOtpRecord; `get_active(user_id)` → SmsOtpRecord\|None; `invalidate(user_id)` → None; `verify_and_delete(user_id, otp_code)` → bool |
| **OAuthLinkRepo** | `OAuthLink` | `get_by_provider_sub(provider, sub)` → OAuthLink\|None; `get_by_user_id(user_id)` → OAuthLink\|None; `create(link)` → OAuthLink; `link_to_existing(user_id, provider_sub, email)` → OAuthLink |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **challenge_token** | Short-lived (5-min) HS256 token proving credentials passed; required for all 2FA and OAuth exchange endpoints; single-use (ADR-018) |
| **TOTP** | Time-based One-Time Password per RFC 6238; SHA-1, 6-digit, 30-second step, ±1 step tolerance |
| **Backup Code** | Single-use 8-char alphanumeric recovery code; 8 generated at 2FA setup; bcrypt-hashed in storage |
| **SMS OTP** | 6-digit numeric one-time password sent via Twilio; 5-minute TTL; max 3 sends per 10-minute window |
| **OAuth Exchange** | Server-side flow converting NextAuth Google session into internal `challenge_token`; does NOT issue JWT directly |
| **Account Linking** | Process of connecting a Google OAuth identity to an existing email+password account; requires password confirmation |
| **2FA Method** | The configured second-factor type (totp or sms); immutable after setup; determines challenge flow |
| **Replay Protection** | Mechanism preventing reuse of the same TOTP code within its validity window; tracked via Redis |
| **Mayorista** | Wholesale buyer user type; the primary user role for this platform |
