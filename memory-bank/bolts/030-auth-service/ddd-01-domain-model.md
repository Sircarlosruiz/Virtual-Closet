---
stage: model
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
---

## Static Model: 001-auth-service

### Entities

- **User**: `id (UUID)`, `email (unique, lowercase)`, `password_hash`, `tenant_id (FK)`, `role`, `email_verified (bool)`, `is_locked (bool)`, `failed_attempts (int)`, `created_at`, `updated_at` - Business Rules: Email must be unique and normalized to lowercase; password must meet complexity requirements (≥8 chars, ≥1 uppercase, ≥1 number); account locks after 5 consecutive failed login attempts; cannot login until email is verified; failed_attempts reset to 0 on successful login.

- **EmailVerificationToken**: `id (UUID)`, `token (unique)`, `user_id (FK)`, `expires_at`, `used (bool)`, `created_at` - Business Rules: Token is single-use; expires 24 hours after creation; only one active token per user at a time (new token invalidates previous); used tokens cannot be reused.

- **UnlockToken**: `id (UUID)`, `token (unique)`, `user_id (FK)`, `expires_at`, `used (bool)`, `created_at` - Business Rules: Token is single-use; expires 24 hours after creation; used tokens cannot be reused; unlocks account by setting `is_locked=false` and `failed_attempts=0`.

### Value Objects

- **Email**: `value (string)` - Constraints: Must be valid email format; normalized to lowercase; uniqueness enforced at repository level.

- **Password**: `hash (string)` - Constraints: Minimum 8 characters; at least 1 uppercase letter; at least 1 number; hashed with bcrypt cost ≥ 12 before storage.

- **BusinessName**: `value (string)` - Constraints: Non-empty string; maximum 255 characters.

- **VerificationToken**: `value (string)` - Constraints: 32-byte random hex; single-use; 24-hour TTL.

- **UnlockTokenValue**: `value (string)` - Constraints: Signed token; single-use; 24-hour TTL.

### Aggregates

- **User Aggregate**: Root: `User` - Members: `User`, `EmailVerificationToken`, `UnlockToken` - Invariants: Email must be unique within tenant; password complexity enforced at creation; email_verified must be true before login; is_locked prevents all login attempts; failed_attempts incremented atomically on each failed login; account locks exactly at 5 failed attempts; successful login resets failed_attempts to 0.

### Domain Events

- **UserRegistered**: Trigger: New user created via registration - Payload: `user_id`, `email`, `tenant_id`, `business_name` - Side Effects: EmailVerificationToken created; verification email sent.

- **EmailVerified**: Trigger: Valid verification token used - Payload: `user_id`, `verified_at` - Side Effects: `email_verified` set to true.

- **LoginFailed**: Trigger: Invalid credentials submitted - Payload: `user_id` or `email`, `failed_attempts`, `is_locked` - Side Effects: `failed_attempts` incremented; account locked if reaches 5.

- **AccountLocked**: Trigger: 5th consecutive failed login - Payload: `user_id`, `locked_at` - Side Effects: `is_locked` set to true; unlock email sent; UnlockToken created.

- **AccountUnlocked**: Trigger: Valid unlock token used - Payload: `user_id`, `unlocked_at` - Side Effects: `is_locked` set to false; `failed_attempts` reset to 0.

- **LoginSucceeded**: Trigger: Valid credentials for verified, unlocked account - Payload: `user_id`, `tenant_id`, `role` - Side Effects: `failed_attempts` reset to 0; challenge_token issued.

### Domain Services

- **RegistrationService**: Operations: `register(email, password, business_name, tenant_id)` - Dependencies: `UserRepository`, `EmailVerificationTokenRepository`, `EmailService`, `TenantRepository` - Responsibilities: Validate email uniqueness; validate password complexity; create User and Tenant atomically; generate and store EmailVerificationToken; trigger verification email.

- **AuthenticationService**: Operations: `authenticate(email, password)`, `verify_email(token)`, `unlock_account(token)` - Dependencies: `UserRepository`, `EmailVerificationTokenRepository`, `UnlockTokenRepository`, `EmailService` - Responsibilities: Validate credentials with timing-safe comparison; enforce lockout policy; manage verification and unlock tokens; issue challenge_token on successful authentication.

- **LockoutService**: Operations: `record_failed_attempt(user_id)`, `lock_account(user_id)`, `unlock_account(user_id)` - Dependencies: `UserRepository` - Responsibilities: Atomically increment failed_attempts; lock account at threshold; generate unlock tokens; send lockout notifications.

### Repository Interfaces

- **UserRepository**: Entity: `User` - Methods: `create(user)`, `find_by_id(id)`, `find_by_email(email)`, `update(user)`, `increment_failed_attempts(user_id)`, `lock(user_id)`, `unlock(user_id)`

- **EmailVerificationTokenRepository**: Entity: `EmailVerificationToken` - Methods: `create(token)`, `find_by_token(token)`, `invalidate_by_user_id(user_id)`, `mark_used(token)`

- **UnlockTokenRepository**: Entity: `UnlockToken` - Methods: `create(token)`, `find_by_token(token)`, `mark_used(token)`

### Ubiquitous Language

- **Mayorista**: A wholesale vendor user type with business account privileges.

- **Tenant**: The organizational unit (business) that a mayorista belongs to; each mayorista has exactly one tenant.

- **Email Verification**: The process of confirming a user's email address ownership via a single-use token sent by email.

- **Challenge Token**: A short-lived (5-min) signed token issued after successful credential validation, encoding `user_id` and `step: credentials_passed`; required to proceed to 2FA.

- **Account Lockout**: A security state triggered after 5 consecutive failed login attempts; prevents all login attempts until unlocked via email link.

- **Failed Attempts**: A counter tracking consecutive unsuccessful login attempts; resets to 0 on successful login.

- **Unlock Token**: A single-use, time-limited (24-hour) signed token sent to a locked account's email to restore access.
