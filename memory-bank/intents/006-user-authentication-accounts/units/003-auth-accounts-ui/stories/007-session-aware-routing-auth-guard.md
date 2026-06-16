---
id: 007-session-aware-routing-auth-guard
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: complete
priority: must
created: 2026-06-08T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 007-session-aware-routing-auth-guard

## User Story

**As a** mayorista using the platform
**I want** protected routes to redirect me to login if I'm not authenticated
**So that** I cannot accidentally access pages that require a valid session

## Acceptance Criteria

- [ ] **Given** I navigate to any protected route (e.g., `/dashboard`, `/generate`) without a valid session, **When** the page resolves, **Then** I am redirected to `/auth/login?redirect={original_path}`
- [ ] **Given** I complete login and 2FA, **When** I am redirected to `/auth/login?redirect=/generate`, **Then** after authentication I land on `/generate` (not the dashboard)
- [ ] **Given** I have a valid session but 2FA is NOT complete (challenge_token state), **When** I navigate to a protected route, **Then** I am redirected to `/auth/2fa/challenge`
- [ ] **Given** my access token is expired, **When** a protected page loads, **Then** the token refresh is attempted silently; if refresh succeeds, page loads normally; if refresh fails, I am redirected to login
- [ ] **Given** I log out, **When** I press the browser back button to a protected page, **Then** I am redirected to login (no stale cache)

## Technical Notes

- Implement via Next.js middleware (`middleware.ts`) for server-side route protection
- Session state: `unauthenticated`, `pending_2fa`, `authenticated`
- NextAuth `auth()` helper in middleware to check session state
- Access token stored in `httpOnly` cookie; refresh handled via `POST /auth/refresh` on 401
- Public routes: `/auth/*`, `/catalog/access`, `/.well-known/*`

## Dependencies

### Requires
- 004-2fa-challenge-screen (2FA state handling)

### Enables
- All protected dashboard features

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User opens two tabs; logs out in one | Other tab redirects to login on next API call (401 triggers re-auth) |
| Redirect loop (login → protected → login) | Detected by checking `redirect` param; cap at 1 redirect |
| Token refresh race between tabs | Concurrent refreshes handled gracefully; first wins |

## Out of Scope

- Role-based access within the dashboard (all authenticated mayoristas and admins have full access to their tenant — future intent)
