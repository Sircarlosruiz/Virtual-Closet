---
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
phase: inception
status: draft
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
---

# Unit Brief: Auth & Accounts UI

## Purpose

All frontend authentication and account management pages for Virtual Closet. Covers the full mayorista auth flow (registration, login, 2FA setup/challenge, password reset), Google OAuth via NextAuth, admin invitation acceptance, buyer catalog access page, and account settings.

## Scope

### In Scope
- Registration page (email+password; Google OAuth button)
- Email verification landing page
- Login page (email+password; Google OAuth button)
- 2FA setup page (QR code for TOTP; SMS fallback setup; backup codes display)
- 2FA challenge page (TOTP input or SMS OTP input)
- Password reset request page + reset form
- Account locked page with unlock instructions
- Admin invitation acceptance page (registration within tenant)
- Buyer catalog access page (link validation → redirect to catalog view)
- Account settings page (view 2FA method, manage admin users, generate buyer links)
- NextAuth configuration (Google provider + custom credentials provider)

### Out of Scope
- Backend API implementation → `001-auth-service`, `002-tenant-account-service`
- Catalog browsing UI → `002-catalog-management` intent
- Subscription/billing UI (future intent)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Registration form + email verification page | Must |
| FR-2 | Login form + lockout error state | Must |
| FR-3 | Google OAuth button + NextAuth integration | Must |
| FR-4 | 2FA setup wizard + challenge screen | Must |
| FR-5 | Admin invite acceptance + admin management in settings | Should |
| FR-6 | Buyer link generation UI + buyer catalog access page | Must |
| FR-7 | Tenant-aware UI (no cross-tenant data displayed) | Must |
| FR-8 | Password reset request + reset form pages | Must |
| FR-9 | Session-aware routing (redirect to login if no valid token) | Must |

---

## Domain Concepts

### Key Pages / Routes

| Route | Purpose | Auth Required |
|-------|---------|---------------|
| `/auth/register` | Mayorista registration form | No |
| `/auth/verify-email` | Email verification landing | No |
| `/auth/login` | Login form | No |
| `/auth/2fa/setup` | 2FA setup wizard (TOTP or SMS) | Partial (after credentials) |
| `/auth/2fa/challenge` | 2FA OTP input | Partial (after credentials) |
| `/auth/forgot-password` | Password reset request | No |
| `/auth/reset-password` | New password form | No (token-gated) |
| `/auth/accept-invitation` | Admin registration via invite link | No (token-gated) |
| `/catalog/access` | Buyer link validation + redirect | No (buyer token) |
| `/settings/account` | 2FA method, admin management | Yes |
| `/settings/buyer-links` | Generate and manage buyer links | Yes |

### Key Components

| Component | Description |
|-----------|-------------|
| `AuthGuard` | HOC/middleware that redirects unauthenticated users |
| `TwoFactorSetup` | Wizard: choose method → configure → confirm → show backup codes |
| `TwoFactorChallenge` | OTP input with fallback toggle (TOTP ↔ SMS) |
| `AdminInviteForm` | Email input + send invitation |
| `AdminList` | Table of current admins with revoke action |
| `BuyerLinkGenerator` | Select catalogs + TTL → generate + copy link |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 8 |
| Must Have | 7 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority |
|----------|-------|----------|
| 001 | Registration & Email Verification Pages | Must |
| 002 | Login Page with Google OAuth | Must |
| 003 | 2FA Setup Wizard | Must |
| 004 | 2FA Challenge Screen | Must |
| 005 | Password Reset Pages | Must |
| 006 | Buyer Catalog Access Page | Must |
| 007 | Session-Aware Routing and Auth Guard | Must |
| 008 | Account Settings — Admin Management & Buyer Links | Should |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| `001-auth-service` | All auth API endpoints (register, login, 2FA, reset, sessions) |
| `002-tenant-account-service` | Admin invite, buyer link generation, tenant settings |

### Depended By
| Unit | Reason |
|------|--------|
| None | Leaf unit |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| NextAuth | Google OAuth session management; custom credentials provider | Medium |
| Google OAuth 2.0 | Social login UI redirect | Medium |

---

## Technical Context

### Suggested Technology
- Next.js 14+ (App Router) — consistent with existing frontend
- NextAuth v5 (`next-auth`) with Google provider + custom credentials provider
- React Hook Form + Zod for form validation
- Existing UI component library (check `frontend/components/`)
- `js-cookie` or `httpOnly` cookie for token storage (align with security requirements)

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| `001-auth-service` | REST API calls | HTTPS / fetch |
| `002-tenant-account-service` | REST API calls | HTTPS / fetch |
| NextAuth | Provider config in `app/api/auth/[...nextauth]/route.ts` | Next.js API route |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| NextAuth session | Cookie (server) | Per session | Session TTL |
| Access token | Memory / httpOnly cookie | Per session | 15 min |
| Refresh token | httpOnly cookie | Per session | 7 days |

---

## Constraints

- Access and refresh tokens stored in `httpOnly; Secure; SameSite=Strict` cookies — no `localStorage`
- 2FA setup must be completed before the mayorista can access any protected route (enforced via `AuthGuard`)
- Buyer access page (`/catalog/access`) must work without any mayorista session
- NextAuth session is NOT sufficient for API access — must exchange for internal JWT after 2FA

---

## Success Criteria

### Functional
- [ ] Full registration → email verify → login → 2FA setup → dashboard flow works end-to-end
- [ ] Google OAuth button completes OAuth, triggers 2FA setup if first login, then redirects to dashboard
- [ ] 2FA challenge correctly validates TOTP and SMS codes; backup code unlocks access
- [ ] Buyer link opens catalog view without login
- [ ] Admin invitation link routes to fresh registration within the correct tenant

### Non-Functional
- [ ] Auth pages load < 2s on first visit (cold cache)
- [ ] No sensitive data (tokens, secrets) stored in localStorage or sessionStorage

### Quality
- [ ] All auth flows tested with Playwright or Cypress E2E
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| bolt-1 | simple-construction-bolt | S001, S002, S005, S007 | Core auth pages (register, login, reset, guard) |
| bolt-2 | simple-construction-bolt | S003, S004 | 2FA setup wizard + challenge screen |
| bolt-3 | simple-construction-bolt | S006, S008 | Buyer access page + account settings |

---

## Notes

- Check existing `frontend/components/` for reusable form and layout components before building new ones
- NextAuth custom credentials provider should call the FastAPI `/auth/login` endpoint; do not reimplement credential validation in Next.js
- The 2FA challenge page is a mid-session state (user has credentials but no JWT) — model this carefully in NextAuth session callbacks
