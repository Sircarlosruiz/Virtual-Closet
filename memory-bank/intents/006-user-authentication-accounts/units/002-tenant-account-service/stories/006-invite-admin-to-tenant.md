---
id: 006-invite-admin-to-tenant
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: draft
priority: should
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 006-invite-admin-to-tenant

## User Story

**As a** mayorista (primary account owner)
**I want** to invite someone to be an admin of my account by email
**So that** they can help me manage the platform without sharing my credentials

## Acceptance Criteria

- [ ] **Given** I am the primary mayorista, **When** I call `POST /tenants/me/admins/invite` with an email, **Then** an `AdminInvitation` record is created with a signed token (7-day TTL) and an invitation email is sent to the provided address
- [ ] **Given** the invitee receives the email and opens the invitation link, **When** they submit registration (name, password), **Then** a new `User` record is created with `role=admin` and `tenant_id` matching the inviting tenant
- [ ] **Given** the invitee already has an account on the platform (different tenant), **When** they open the invitation link, **Then** they are informed they must use a separate email (one account per person per platform is not enforced — invitee registers a new account scoped to this tenant)
- [ ] **Given** an invitation expires (>7 days), **When** the invitee opens the link, **Then** they see "Invitation expired; please ask the account owner to resend"
- [ ] **Given** the invitation is accepted, **When** the admin registers, **Then** the same 2FA setup requirement applies (redirected to 2FA setup on first login)

## Technical Notes

- Invitation token: 32-byte hex, stored in `AdminInvitation`, expires 7 days, single-use
- Invitation acceptance endpoint: `POST /auth/accept-invitation` (public, token-gated)
- Admin user created with `role=admin`, `tenant_id` set to inviting tenant
- Invitation email contains: `{FRONTEND_URL}/auth/accept-invitation?token={token}`
- Rate limit: max 10 pending invitations per tenant at a time

## Dependencies

### Requires
- 001-create-manage-tenant

### Enables
- 007-revoke-admin-access

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Majority of invited email is already an admin in this tenant | Error: "This email is already an admin of your account" |
| Inviter loses mayorista role before invitee accepts | Invitation still valid if tenant is active |

## Out of Scope

- Inviting admins with custom permissions (all admins have full access — future intent)
- Invitee using Google OAuth for their admin account (possible but must accept invitation first via email)
