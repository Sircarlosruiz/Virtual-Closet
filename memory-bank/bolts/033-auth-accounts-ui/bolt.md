---
id: 033-auth-accounts-ui
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
type: simple-construction-bolt
status: planned
stories:
  - 001-registration-email-verification-pages
  - 002-login-page-google-oauth
  - 005-password-reset-pages
  - 007-session-aware-routing-auth-guard
created: 2026-06-08T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [030-auth-service, 031-auth-service, 032-auth-service]
enables_bolts: [034-auth-accounts-ui]
requires_units: []
blocks: true

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 033-auth-accounts-ui

### Objective

Implement core auth pages and session infrastructure: registration form, email verification landing, login page with Google OAuth button (NextAuth), password reset pages, and the Next.js middleware auth guard for protected routes.

### Stories Included

- [ ] **001-registration-email-verification-pages**: Registration Form + Email Verification Landing — Priority: Must
- [ ] **002-login-page-google-oauth**: Login Page with Google OAuth Button (NextAuth) — Priority: Must
- [ ] **005-password-reset-pages**: Forgot Password + Reset Password Pages — Priority: Must
- [ ] **007-session-aware-routing-auth-guard**: Next.js Middleware Auth Guard + Session-Aware Routing — Priority: Must

### Expected Outputs

- `/auth/register` page (React Hook Form + Zod validation)
- `/auth/verify-email` landing page
- `/auth/login` page (credentials + Google OAuth button)
- `/auth/forgot-password` + `/auth/reset-password` pages
- `middleware.ts` (Next.js route protection)
- NextAuth configuration (`app/api/auth/[...nextauth]/route.ts`) with Google + credentials providers
- Token storage in `httpOnly` cookies

### Dependencies

#### Bolt Dependencies (within intent)
- **030-auth-service** (Required): Register + login endpoints must exist
- **031-auth-service** (Required): OAuth exchange endpoint must exist
- **032-auth-service** (Required): JWT + refresh endpoints must exist for session guard

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- 034-auth-accounts-ui (2FA pages build on top of auth infrastructure)
