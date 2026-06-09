---
id: 005-password-reset-pages
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 005-password-reset-pages

## User Story

**As a** mayorista who forgot their password
**I want** dedicated pages to request and complete a password reset
**So that** I can regain access without contacting support

## Acceptance Criteria

- [ ] **Given** I click "Forgot password" on the login page, **When** I am taken to `/auth/forgot-password`, **Then** I see a single email input and a "Send reset link" button
- [ ] **Given** I submit any email (valid or not), **When** the API responds, **Then** I see an identical confirmation message: "If that email is registered, you'll receive a reset link shortly" (no enumeration)
- [ ] **Given** I click the reset link in the email, **When** I land on `/auth/reset-password?token={token}`, **Then** I see a form with new password and confirm password fields
- [ ] **Given** I submit a valid new password, **When** the API confirms, **Then** I see "Password updated successfully" and am redirected to login after 3 seconds
- [ ] **Given** the reset token is expired or already used, **When** the page loads, **Then** I see "This link has expired. Request a new one." with a link back to `/auth/forgot-password`

## Technical Notes

- Routes: `/auth/forgot-password`, `/auth/reset-password`
- Password field: same validation as registration (≥8 chars, ≥1 uppercase, ≥1 number)
- Token passed via URL query param; validated on form load (pre-flight check to avoid form completion before discovering expiry)

## Dependencies

### Requires
- 002-login-page-google-oauth

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User is already logged in and visits forgot-password | Allow access (they may be resetting for a different reason) |
| User navigates to reset-password without a token | Redirect to `/auth/forgot-password` |

## Out of Scope

- Google-only accounts (shown message to use Google login on forgot-password page)
