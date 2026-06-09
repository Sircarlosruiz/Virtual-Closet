---
id: 001-registration-email-verification-pages
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: draft
priority: must
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 001-registration-email-verification-pages

## User Story

**As a** new wholesale vendor
**I want** a registration form and email verification page
**So that** I can create my Virtual Closet account

## Acceptance Criteria

- [ ] **Given** I navigate to `/auth/register`, **When** the page loads, **Then** I see a form with fields: Business Name, Email, Password (with show/hide), Password Confirm; plus a "Continue with Google" button
- [ ] **Given** I submit valid registration data, **When** the API call succeeds, **Then** I am redirected to a confirmation screen: "Check your inbox — we've sent a verification link to {email}"
- [ ] **Given** I submit invalid data (missing fields, weak password, mismatched confirm), **When** I click Submit, **Then** inline validation errors appear per field before the API is called
- [ ] **Given** the API returns an error (e.g., email taken), **When** the response is processed, **Then** a non-enumerating error message is shown at the top of the form
- [ ] **Given** I navigate to `/auth/verify-email?token={token}`, **When** the token is valid, **Then** I see a success message and am redirected to `/auth/login` after 3 seconds
- [ ] **Given** the token is expired or invalid, **When** the page loads, **Then** I see an error with a "Resend verification email" link

## Technical Notes

- Route: `/auth/register`, `/auth/verify-email`
- Use React Hook Form + Zod for client-side validation
- Password strength indicator (optional but recommended)
- Check `frontend/components/` for existing form primitives before creating new ones

## Dependencies

### Requires
- None (entry point)

### Enables
- 002-login-page-google-oauth

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User navigates back after submitting registration | Re-submission prevention (disable submit button on pending state) |
| Slow network during form submission | Loading spinner on submit button |

## Out of Scope

- Admin invitation acceptance page (story 008 account settings, or dedicated story)
