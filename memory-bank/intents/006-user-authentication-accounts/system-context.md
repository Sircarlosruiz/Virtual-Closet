---
intent: 006-user-authentication-accounts
phase: inception
status: context-defined
updated: 2026-06-08T00:00:00Z
---

# User Authentication & Mayorista Accounts - System Context

## System Overview

The Authentication & Accounts system provides foundational identity management for Virtual Closet. It introduces multi-tenancy (`tenant_id`) across the platform, handles mayorista registration and login via email+password or Google OAuth (NextAuth), enforces mandatory TOTP 2FA with SMS fallback, manages admin sub-roles within mayorista tenants, and grants buyers stateless catalog access via signed JWT links — without requiring buyer accounts.

## Context Diagram

```mermaid
C4Context
    title System Context - User Authentication & Mayorista Accounts

    Person(mayorista, "Mayorista", "Wholesale vendor. Registers, logs in (email+Google), completes 2FA, manages their tenant.")
    Person(admin, "Mayorista Admin", "Delegated admin within a mayorista tenant. Invited by the primary mayorista.")
    Person(buyer, "Buyer / Customer", "Accesses shared catalog via a signed email link. No account required.")

    System(auth, "Auth & Accounts System", "Handles registration, login, 2FA, JWT issuance, tenant isolation, and buyer link generation.")

    System_Ext(nextauth, "NextAuth (Next.js)", "Server-side OAuth session management for the frontend. Exchanges Google token for internal JWT after 2FA.")
    System_Ext(google, "Google OAuth 2.0", "Social login provider. Returns identity token to NextAuth.")
    System_Ext(postgres, "PostgreSQL", "Stores users, tenants, roles, refresh token records, and 2FA secrets.")
    System_Ext(redis, "Redis", "Refresh token denylist for fast invalidation on logout / password reset.")
    System_Ext(email_svc, "Email Service (SES/SendGrid)", "Delivers verification emails, password reset links, admin invitations, and buyer catalog links.")
    System_Ext(sms_svc, "SMS Provider (Twilio)", "Delivers OTP codes for SMS-based 2FA fallback.")

    Rel(mayorista, auth, "Registers, logs in, completes 2FA, manages account", "HTTPS / REST + NextAuth")
    Rel(admin, auth, "Logs in via invitation link, manages tenant settings", "HTTPS / REST + NextAuth")
    Rel(buyer, auth, "Accesses catalog via signed JWT link (read-only)", "HTTPS / REST")

    Rel(auth, nextauth, "Issues internal JWT after 2FA; validates NextAuth session", "Server-to-server / Next.js API route")
    Rel(nextauth, google, "Redirects for OAuth authorization; receives identity token", "OAuth 2.0 / HTTPS")
    Rel(auth, postgres, "Persists users, tenants, 2FA secrets, refresh token records", "SQL / asyncpg")
    Rel(auth, redis, "Stores and checks refresh token denylist", "Redis protocol")
    Rel(auth, email_svc, "Sends verification, reset, invitation, and buyer-link emails", "SMTP / REST API")
    Rel(auth, sms_svc, "Sends SMS OTP for 2FA fallback", "REST API")
```

## External Integrations

| System | Direction | Data Exchanged | Protocol | Risk |
|--------|-----------|----------------|----------|------|
| **Google OAuth 2.0** | Outbound (redirect) + Inbound (token) | Identity token (email, name, sub) | OAuth 2.0 / HTTPS | Medium |
| **NextAuth (Next.js)** | Bidirectional | Google identity → NextAuth session → internal JWT | Server-to-server / Next.js API routes | Medium |
| **PostgreSQL** | Outbound (read/write) | Users, tenants, roles, 2FA secrets, refresh tokens | SQL / asyncpg | Low |
| **Redis** | Outbound (read/write) | Refresh token JTI denylist | Redis protocol | Low |
| **Email Service (SES/SendGrid)** | Outbound | Verification links, reset links, invitations, buyer catalog URLs | SMTP / REST | Medium |
| **SMS Provider (Twilio)** | Outbound | 6-digit OTP codes | REST API | Medium |

## High-Level Constraints

- **`tenant_id` is introduced here** — all existing and future entities (`media`, `catalogs`, `jobs`, `batches`) must be backfilled or schema-migrated to include `tenant_id` as a foreign key to the new `tenants` table
- **NextAuth handles Google OAuth session on the frontend** — backend issues its own JWT only after NextAuth session is verified AND 2FA is passed; the NextAuth session alone does not grant API access
- **2FA is mandatory for all mayorista and admin roles** — no route to skip or defer; enforced at the JWT issuance step, not per-endpoint
- **Buyer tokens are catalog-scoped JWTs** — signed with a per-tenant secret; no server-side state for buyer sessions
- All endpoints require HTTPS; auth cookies (if any) are `SameSite=Strict; Secure; HttpOnly`
- SMS OTP is a fallback only; TOTP setup is presented first

## Key NFR Goals

- Login + 2FA flow end-to-end < 1s (p95) under normal load
- Refresh token validation < 150ms (p95) including Redis denylist check
- Zero cross-tenant data leakage — enforced at ORM layer and validated by integration tests
- Refresh token denylist supports instant revocation (< 50ms Redis write)
- Email delivery for verification and reset < 30 seconds (provider SLA)
