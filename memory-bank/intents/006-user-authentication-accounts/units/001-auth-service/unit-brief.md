---
unit: 001-auth-service
intent: 006-user-authentication-accounts
phase: inception
status: complete
created: 2026-06-08T00:00:00.000Z
updated: 2026-06-08T00:00:00.000Z
---

# Unit Brief: Auth Service

## Purpose

Core authentication engine for Virtual Closet. Handles mayorista credential registration, email+password and Google OAuth login via NextAuth, mandatory TOTP 2FA with SMS fallback, password reset, and JWT session lifecycle (issuance, refresh rotation, revocation).

## Scope

### In Scope
- Mayorista registration (email+password) with email verification
- Login with email+password; account lockout after 5 failures
- Google OAuth 2.0 via NextAuth — session exchange to internal JWT after 2FA
- TOTP 2FA setup (QR + secret) and challenge; SMS OTP as fallback
- Backup recovery codes (8 single-use) generated at 2FA setup
- Password reset via single-use time-limited email link
- JWT issuance: RS256, 15-min access token + 7-day rotating refresh token
- Logout (single-device) and all-devices logout
- Refresh token denylist (Redis)
- 2FA enforcement — no JWT issued until 2FA passed

### Out of Scope
- Tenant model and `tenant_id` introduction → `002-tenant-account-service`
- Admin sub-role management → `002-tenant-account-service`
- Buyer token generation → `002-tenant-account-service`
- Subscription or plan management (future intent)
- Frontend pages → `003-auth-accounts-ui`

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Mayorista registration (email+password + email verification) | Must |
| FR-2 | Mayorista login + account lockout after 5 failed attempts | Must |
| FR-3 | Google OAuth via NextAuth; 2FA still required post-OAuth | Must |
| FR-4 | Mandatory TOTP 2FA + SMS OTP fallback; backup codes | Must |
| FR-8 | Password reset via single-use email link (1-hour TTL) | Must |
| FR-9 | JWT sessions — 15min access / 7-day rotating refresh; Redis denylist | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `User` | A registered mayorista or admin | `id`, `email`, `password_hash`, `tenant_id`, `role`, `email_verified`, `is_locked`, `failed_attempts`, `created_at` |
| `TwoFactorConfig` | 2FA setup per user | `user_id`, `method` (totp/sms), `totp_secret`, `phone_number`, `is_configured`, `backup_codes[]` |
| `RefreshToken` | Issued refresh token record | `jti`, `user_id`, `expires_at`, `revoked` |
| `EmailVerificationToken` | Single-use email confirmation token | `token`, `user_id`, `expires_at`, `used` |
| `PasswordResetToken` | Single-use password reset token | `token`, `user_id`, `expires_at`, `used` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `register` | Create user + send verification email | email, password, business_name | user (unverified), email sent |
| `verify_email` | Activate account via token | token | user (verified) |
| `login` | Validate credentials → 2FA challenge | email, password | 2FA challenge token |
| `complete_2fa` | Validate TOTP/SMS OTP → issue JWT | challenge_token, otp_code | access_token, refresh_token |
| `oauth_exchange` | Exchange NextAuth session for JWT after 2FA | nextauth_session | access_token, refresh_token |
| `setup_2fa` | Configure TOTP (generate QR) or SMS (send OTP) | user_id, method | qr_uri or sms_sent, backup_codes |
| `refresh_token` | Rotate refresh token → new access token | refresh_token | new access_token, new refresh_token |
| `logout` | Revoke current refresh token | refresh_token | success |
| `logout_all` | Revoke all refresh tokens for user | user_id | success |
| `reset_password` | Initiate or complete password reset | email or (token, new_password) | email sent or success |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 9 |
| Must Have | 9 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority |
|----------|-------|----------|
| 001 | Mayorista Registration | Must |
| 002 | Email Verification | Must |
| 003 | Login with Email + Password | Must |
| 004 | Account Lockout on Failed Attempts | Must |
| 005 | TOTP 2FA Setup and Challenge | Must |
| 006 | SMS OTP 2FA Fallback | Must |
| 007 | Google OAuth Login via NextAuth | Must |
| 008 | Password Reset Flow | Must |
| 009 | JWT Session Management and Logout | Must |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| `002-tenant-account-service` | Needs `tenant_id` on user creation; tenant lookup on login |

### Depended By
| Unit | Reason |
|------|--------|
| `003-auth-accounts-ui` | Consumes all auth API endpoints |
| All platform services | JWT validation; all routes require valid `tenant_id` claim |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| Google OAuth 2.0 (via NextAuth) | Social login identity | Medium |
| Redis | Refresh token denylist | Low |
| Email Service (SES/SendGrid) | Verification + reset emails | Medium |
| SMS Provider (Twilio) | SMS OTP delivery | Medium |

---

## Technical Context

### Suggested Technology
- FastAPI + SQLAlchemy (async) — consistent with existing backend
- `python-jose` or `authlib` for JWT (RS256)
- `pyotp` for TOTP generation and validation
- `passlib[bcrypt]` for password hashing (cost ≥ 12)
- `redis-py` for refresh token denylist
- NextAuth Google provider on frontend (Next.js)

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| `002-tenant-account-service` | Service call | Internal Python / DB query |
| Redis | Cache | Redis protocol |
| Email Service | Outbound | REST API (SendGrid) / SMTP |
| SMS Provider | Outbound | REST API (Twilio) |
| NextAuth | Token exchange | Next.js API route → FastAPI |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Users | PostgreSQL | Low (< 100k) | Permanent |
| 2FA configs | PostgreSQL | 1:1 with users | Permanent |
| Refresh tokens | PostgreSQL + Redis denylist | Low | 7 days |
| Email/reset tokens | PostgreSQL | Low | 1 hour TTL |

---

## Constraints

- 2FA cannot be skipped — no JWT issued without completed 2FA challenge
- Password hashing with bcrypt cost ≥ 12; no MD5/SHA1
- JWTs signed with RS256 asymmetric keys; public key at `/.well-known/jwks.json`
- Account lockout after 5 consecutive failures; unlock only via email
- `002-tenant-account-service` must be deployed before this unit (requires tenants table)

---

## Success Criteria

### Functional
- [ ] Mayorista can register, verify email, and log in
- [ ] Google OAuth login works via NextAuth and results in an internal JWT
- [ ] 2FA TOTP and SMS OTP both work; backup codes unlock access
- [ ] Password reset invalidates all active refresh tokens
- [ ] Logout single-device and all-devices both revoke tokens immediately

### Non-Functional
- [ ] Login + 2FA end-to-end < 1s (p95)
- [ ] Refresh token validation < 150ms including Redis denylist
- [ ] Zero user enumeration in login, registration, and reset responses

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| bolt-1 | ddd-construction-bolt | S001, S002, S003, S004 | User entity + registration + login + lockout |
| bolt-2 | ddd-construction-bolt | S005, S006, S007 | 2FA (TOTP + SMS) + OAuth exchange |
| bolt-3 | ddd-construction-bolt | S008, S009 | Password reset + session management |

---

## Notes

- `002-tenant-account-service` must be built first; this unit cannot run standalone migrations without the tenants table
- NextAuth session exchange pattern: NextAuth callback calls a FastAPI `/auth/oauth/exchange` endpoint, passing the Google identity; FastAPI verifies, creates/fetches the user, then requires 2FA before issuing tokens
- RS256 key pair should be generated and stored as environment secrets at project setup
