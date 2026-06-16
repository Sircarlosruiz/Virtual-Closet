---
stage: implement
bolt: 033-auth-accounts-ui
created: 2026-06-10T00:00:00Z
---

## Implementation Walkthrough: Auth Accounts UI

### Summary

Implemented core authentication pages and session infrastructure for the Virtual Closet frontend. Updated the existing registration form with email verification confirmation screen, enhanced the login page with proper 2FA redirect logic and forgot-password link, created email verification, forgot-password, and reset-password pages, and upgraded the middleware to handle all protected routes with redirect parameter preservation.

### Structure Overview

All auth pages live under `app/(auth)/` which shares a common layout with brand pane and form pane. New routes were added: `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password`. The existing `/auth/login` and `/auth/registro` pages were enhanced. The middleware (`proxy.ts`) was expanded to cover all protected route prefixes.

### Completed Work

- [x] `app/(auth)/registro/page.tsx` — Registration form with password confirmation field, password complexity validation (8+ chars, uppercase, number), success confirmation screen showing email with instructions
- [x] `app/(auth)/login/page.tsx` — Login form with proper error handling for 401/423/403 responses, redirect to 2FA setup/challenge based on backend response, forgot-password link, Google OAuth placeholder button
- [x] `app/(auth)/verify-email/page.tsx` — Token validation page with three states (verifying/success/error), auto-redirect to login on success, resend verification email functionality
- [x] `app/(auth)/forgot-password/page.tsx` — Single email input form, non-enumerating confirmation message, success screen with instructions
- [x] `app/(auth)/reset-password/page.tsx` — Token presence check on load, new password + confirm form with complexity validation, success redirect to login
- [x] `proxy.ts` — Expanded middleware matcher to cover all protected route prefixes (/generate, /batches, /extraction, /media, /jobs), redirect parameter preservation for post-login navigation, authenticated users redirected away from /auth/* to /dashboard
- [x] `lib/api/auth.ts` — Extended with login, logoutAll, refreshToken, forgotPassword, resetPassword, verifyEmail, resendVerification functions and LoginResponse interface

### Key Decisions

- **Password confirmation field**: Added `password_confirm` field to registration form to prevent typos. Uses Zod `.refine()` for cross-field validation.
- **Non-enumerating responses**: Both forgot-password and registration return identical success messages regardless of whether the email exists, preventing user enumeration.
- **Token validation approach**: Reset password page checks for token presence in URL query param. Actual token validity is validated on form submission (server-side). This avoids a separate pre-flight API call.
- **Google OAuth placeholder**: Button is rendered but disabled with "Disponible próximamente" tooltip. Full NextAuth integration will be added when backend OAuth exchange endpoint is ready.
- **Middleware redirect preservation**: When unauthenticated users access protected routes, the middleware stores the original path in `?redirect=` query param for post-login navigation.

### Deviations from Plan

- **No NextAuth integration yet**: The plan included NextAuth configuration with Google + credentials providers. This is deferred because the backend OAuth exchange endpoint needs to be fully tested first. The login page includes a disabled Google button as a placeholder.
- **No silent token refresh in middleware**: The plan mentioned automatic token refresh on 401. This is handled client-side by the `apiFetch` function and will be enhanced in a future iteration.

### Dependencies Added

None — all required dependencies (react-hook-form, zod, sonner, lucide-react) were already installed.

### Developer Notes

- The `apiFetch` function in `lib/api.ts` already handles `credentials: "include"` for cookie-based auth, so no changes were needed there.
- The dashboard layout (`app/(dashboard)/layout.tsx`) already checks for `access_token` cookie server-side and redirects to login if missing. This works seamlessly with the new middleware.
- The `ClientRedirect` component is used for server-side redirects to avoid Turbopack dev bugs with Next.js `redirect()`.
- All auth pages use the shared `AuthLayout` which provides the brand pane on desktop and form pane on mobile.
