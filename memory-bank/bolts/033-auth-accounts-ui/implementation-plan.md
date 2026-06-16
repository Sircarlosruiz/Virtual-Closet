---
stage: plan
bolt: 033-auth-accounts-ui
created: 2026-06-10T00:00:00Z
---

## Implementation Plan: Auth Accounts UI

### Objective

Implement core authentication pages and session infrastructure for the Virtual Closet frontend: registration form with email verification, login page with Google OAuth, password reset flow, and Next.js middleware auth guard for protected routes.

### Deliverables

1 - `/auth/register` page — Registration form with React Hook Form + Zod validation, Google OAuth button, success confirmation screen
2 - `/auth/verify-email` page — Token validation, success/error states, auto-redirect to login, resend link
3 - `/auth/login` page — Email/password form, Google OAuth button, error handling for invalid credentials/locked accounts
4 - `/auth/forgot-password` page — Single email input, no-enumeration confirmation message
5 - `/auth/reset-password` page — Token pre-flight check, new password + confirm form, success redirect
6 - `middleware.ts` — Next.js route protection with session state handling (unauthenticated, pending_2fa, authenticated)
7 - `app/api/auth/[...nextauth]/route.ts` — NextAuth configuration with Google + credentials providers
8 - Token storage in `httpOnly` cookies, silent refresh on 401

### Dependencies

- **030-auth-service**: Register + login endpoints (`POST /api/auth/register`, `POST /api/auth/login`)
- **031-auth-service**: OAuth exchange endpoint (`POST /api/auth/oauth/exchange`), 2FA setup/challenge endpoints
- **032-auth-service**: JWT session endpoints (`POST /api/auth/refresh`, `POST /api/auth/logout`), JWKS endpoint
- **NextAuth v5**: `next-auth@beta` for session management
- **React Hook Form + Zod**: Form validation
- **shadcn/ui**: Existing UI components (button, input, card, form, alert)

### Technical Approach

1 - **NextAuth Configuration**: Custom credentials provider that calls `POST /api/auth/login` and stores `challenge_token` in session. Google provider configured for OAuth. Session state tracks `pending_2fa` vs `authenticated`.
2 - **Form Validation**: React Hook Form + Zod schemas for registration, login, password reset. Shared password validation schema.
3 - **API Client**: Centralized `lib/api-client.ts` for backend calls with automatic refresh token handling on 401.
4 - **Middleware**: `middleware.ts` checks NextAuth session, redirects based on state. Public routes: `/auth/*`, `/.well-known/*`, `/catalog/access`.
5 - **Cookie Strategy**: Access token in `httpOnly` cookie (set by backend), refresh token in `httpOnly` cookie. Frontend reads session state from NextAuth, not directly from cookies.
6 - **Error Handling**: Non-enumerating error messages on registration and forgot-password. Generic "Invalid email or password" on login.

### Acceptance Criteria

- [ ] Registration form validates all fields client-side before API call
- [ ] Registration success shows confirmation screen with email
- [ ] Email verification validates token, shows success/error, redirects appropriately
- [ ] Login form handles credentials + Google OAuth, redirects to 2FA flow
- [ ] Forgot password shows identical response for any email
- [ ] Reset password validates token on load, updates password, redirects to login
- [ ] Middleware redirects unauthenticated users to login with redirect param
- [ ] Middleware redirects pending_2fa users to 2FA challenge
- [ ] Silent token refresh on 401, fallback to login on refresh failure
- [ ] Logout clears session and redirects to login
