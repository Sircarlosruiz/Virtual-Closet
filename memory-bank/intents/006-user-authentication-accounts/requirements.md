---
intent: 006-user-authentication-accounts
phase: inception
status: inception-complete
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
---

# Requirements: User Authentication & Mayorista Accounts

## Intent Overview

Foundational identity and access management for the Virtual Closet B2B platform. Mayoristas (wholesale vendors) register and log in via email+password or Google OAuth, with mandatory two-factor authentication (2FA). Each mayorista account is a fully isolated tenant — its media, catalogs, and jobs are invisible to other mayoristas. Within a mayorista account, one or more admin users can manage settings and sub-users. Buyers/customers do not have traditional accounts; they receive a time-limited, signed email link granting read-only access to the specific catalogs the mayorista has shared with them.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Secure mayorista access with 2FA | 100% of mayorista sessions require 2FA before accessing protected routes | Must |
| Support email+password and Google OAuth | Both methods work at registration and login | Must |
| Full data isolation per mayorista tenant | Zero cross-tenant data leakage verified by integration tests | Must |
| Frictionless buyer catalog access via email link | Buyers access catalogs without creating an account | Must |
| Admin sub-role per mayorista account | Mayorista can designate admins who manage account settings/users | Should |

---

## Functional Requirements

### FR-1: Mayorista Registration (Email + Password)
- **Description**: A new mayorista can create an account using a business email address and a password. The system sends a verification email before the account is activated.
- **Acceptance Criteria**:
  - Registration form accepts email, password (min 8 chars, 1 uppercase, 1 number), and business name
  - Duplicate email addresses are rejected with a clear error
  - Verification email is sent on registration; account is inactive until email is confirmed
  - After verification, mayorista is redirected to onboarding/dashboard
- **Priority**: Must

### FR-2: Mayorista Login (Email + Password)
- **Description**: A registered mayorista logs in with their verified email and password. After credential validation, the system enforces 2FA before granting session access.
- **Acceptance Criteria**:
  - Correct credentials advance to the 2FA challenge step
  - Invalid credentials return a generic error (no user enumeration)
  - Account is locked after 5 consecutive failed attempts; unlock via email
  - Successful 2FA completion issues a JWT access token (15-min TTL) and refresh token (7-day TTL)
- **Priority**: Must

### FR-3: Google OAuth Login / Registration (via NextAuth)
- **Description**: Mayoristas can register or log in using their Google account via NextAuth (server-side OAuth 2.0). On first login, an account is auto-created (verified, no email step). Subsequent logins match by email.
- **Acceptance Criteria**:
  - "Continue with Google" button triggers NextAuth Google provider flow (server-side, no PKCE needed)
  - First-time Google login creates a mayorista account and prompts for business name
  - Existing email (registered via password) linked to Google on first Google login (with confirmation prompt)
  - 2FA is still required after OAuth — NextAuth session is pending until 2FA challenge is passed
  - NextAuth session is exchanged for internal JWT (access + refresh) after 2FA completion
- **Priority**: Must

### FR-4: Two-Factor Authentication (2FA) for Mayoristas
- **Description**: All mayorista accounts must configure and use TOTP-based 2FA (e.g., Google Authenticator, Authy) as the primary method, with SMS OTP as a fallback. 2FA setup is enforced on first login if not yet configured.
- **Acceptance Criteria**:
  - First login after account verification triggers mandatory 2FA setup; user chooses TOTP or SMS
  - TOTP codes are validated with a 30-second window (±1 step tolerance)
  - SMS OTP codes are 6-digit, valid for 5 minutes, rate-limited to 3 requests per 10 minutes
  - Backup recovery codes (8 single-use codes) are generated at setup regardless of 2FA method
  - 2FA cannot be disabled by the mayorista (admin-only operation in a future intent)
  - 2FA challenge is presented before any protected route is accessible
- **Priority**: Must

### FR-5: Mayorista Admin Sub-Role
- **Description**: The account owner (primary mayorista) can designate other users within their tenant as admins. Admins have full access to the mayorista's account settings, users, and data but cannot delete the primary account.
- **Acceptance Criteria**:
  - Primary mayorista can invite admins by email
  - Admin invitation email contains a sign-up link scoped to the mayorista's tenant
  - Admins have the same auth requirements as mayoristas (email+password or Google, 2FA)
  - Primary mayorista can revoke admin access; revocation immediately invalidates active sessions
  - Admin role is visible in the JWT claims (`role: admin`, `tenant_id: {uuid}`)
- **Priority**: Should

### FR-6: Buyer / Customer Token-Based Access
- **Description**: Buyers do not create traditional accounts. When a mayorista shares a catalog, the system generates a signed, time-limited URL (JWT token embedded in link) granting read-only access to that specific catalog.
- **Acceptance Criteria**:
  - Buyer link is valid for 30 days (configurable per mayorista)
  - Link is scoped to specific catalog IDs — accessing other catalogs or routes returns 403
  - Expired or invalid tokens return a clear "link expired" page with instructions to contact the mayorista
  - Buyer sessions are stateless (no server-side session storage for buyers)
  - No account creation, password, or 2FA required for buyers
- **Priority**: Must

### FR-7: Multi-Tenant Data Isolation
- **Description**: Every data record (media, catalogs, jobs, users) is tagged with `tenant_id`. API middleware rejects any query that would return data belonging to a different tenant.
- **Acceptance Criteria**:
  - All database queries include `tenant_id` filter enforced at the ORM/repository layer
  - JWT access tokens include `tenant_id` and `role` claims
  - Attempting to access another tenant's resource returns 404 (not 403, to prevent enumeration)
  - Integration tests verify cross-tenant isolation for all major entity types
- **Priority**: Must

### FR-8: Password Reset
- **Description**: A mayorista who has forgotten their password can reset it via a time-limited email link.
- **Acceptance Criteria**:
  - "Forgot password" flow sends a reset link (valid 1 hour) to the registered email
  - Reset link is single-use; reuse returns an error
  - After reset, all existing refresh tokens for the account are invalidated
  - Response to "forgot password" request is identical whether or not the email exists (no enumeration)
- **Priority**: Must

### FR-9: Session Management & Logout
- **Description**: JWT-based stateless sessions for mayoristas. Access tokens are short-lived; refresh tokens are rotated. Logout invalidates the refresh token.
- **Acceptance Criteria**:
  - Access token TTL: 15 minutes
  - Refresh token TTL: 7 days; rotated on each use
  - Logout endpoint invalidates (server-side denylist) the current refresh token
  - All devices logout invalidates all refresh tokens for the account
  - Token refresh without a valid refresh token returns 401
- **Priority**: Must

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Login endpoint latency | p95 | < 500ms |
| Token refresh latency | p95 | < 200ms |
| Buyer link validation | p95 | < 150ms |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Password hashing | bcrypt (cost ≥ 12) | Argon2id acceptable |
| Token signing | RS256 JWT | Asymmetric keys; public key exposed at /.well-known/jwks.json |
| 2FA | TOTP RFC 6238 | 30-second step, SHA-1, 6-digit code |
| Buyer link signing | HS256 JWT with catalog-scoped claims | Short secret per tenant |
| Transport | HTTPS only | HSTS enforced |
| OAuth | OAuth 2.0 with PKCE | State parameter for CSRF protection |

### Scalability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Concurrent mayorista sessions | Active JWTs | 10,000+ (stateless) |
| Tenant count | Mayorista accounts | 10,000+ |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Auth service availability | Uptime | 99.9% |
| Email delivery (verification, reset) | Delivery rate | > 99% |

### Compliance
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Password policy | NIST SP 800-63B | No forced periodic rotation; breach detection preferred |
| Data residency | TBD | Follow project-wide standard |

---

## Constraints

### Technical Constraints
- Must integrate with existing FastAPI backend and Next.js frontend
- Refresh token denylist requires a Redis store (or DB table if Redis unavailable)
- Google OAuth credentials (client ID/secret) must be provisioned before FR-3 can be deployed

### Business Constraints
- Subscription tiers are OUT OF SCOPE — this intent does not restrict features by plan
- Buyers have no self-service account management — all buyer access is controlled by the mayorista

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Platform has no existing auth layer to migrate — starting fresh | Migration complexity if old tokens exist | Audit existing auth code before construction |
| Email delivery via existing provider (e.g., SendGrid/SES) already configured | Delays if email infra needs setup | Confirm provider before FR-1 construction |
| Multi-tenancy is enforced at API layer (not DB-level row security) | Cross-tenant leaks harder to prevent at API layer | Consider Postgres RLS as defense-in-depth |
| Google OAuth app registration is or will be approved by project owner | FR-3 blocked without credentials | Create OAuth app registration early |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should SMS-based 2FA be offered as an alternative to TOTP? | Carlos | 2026-06-08 | ✅ SMS as fallback; TOTP is primary |
| Is PKCE required for the Next.js OAuth flow, or is server-side OAuth handled by a library (e.g., NextAuth)? | Carlos | 2026-06-08 | ✅ NextAuth (server-side) |
| Is there an existing `tenant_id` concept in the DB schema, or must it be introduced? | Carlos | 2026-06-08 | ✅ No existing concept — must be introduced in this intent |
| Should admin invitation require the invitee to already have a mayorista account, or is it a fresh registration? | Carlos | 2026-06-08 | ✅ Fresh registration within the tenant (no prior account needed) |
