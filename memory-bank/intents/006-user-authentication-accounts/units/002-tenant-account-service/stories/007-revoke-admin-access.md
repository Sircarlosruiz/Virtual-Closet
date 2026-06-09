---
id: 007-revoke-admin-access
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
status: draft
priority: should
created: 2026-06-08T00:00:00Z
assigned_bolt: null
implemented: false
---

# Story: 007-revoke-admin-access

## User Story

**As a** mayorista (primary account owner)
**I want** to remove an admin's access to my account
**So that** former employees or collaborators can no longer access my data

## Acceptance Criteria

- [ ] **Given** I am the primary mayorista and have at least one admin, **When** I call `DELETE /tenants/me/admins/{admin_user_id}`, **Then** the admin's `role` is set to `revoked`, all their active refresh tokens are invalidated, and they are added to the Redis denylist
- [ ] **Given** a revoked admin tries to access any platform route, **When** their (still-valid) access token is used, **Then** the token is rejected on the next refresh attempt (short access token TTL = max 15 min exposure window)
- [ ] **Given** I call `GET /tenants/me/admins`, **When** the request is processed, **Then** I receive a list of all active admins (not revoked) in my tenant
- [ ] **Given** I attempt to revoke the primary mayorista account, **When** the request is processed, **Then** a 403 is returned: "Cannot revoke the primary account owner"

## Technical Notes

- Revocation: set `user.role = "revoked"`, revoke all `RefreshToken` records for the user
- Redis denylist: add all active refresh token JTIs to denylist with their remaining TTL
- Access tokens (15-min) cannot be immediately revoked — this is accepted behavior; 15-min window is tolerable
- Endpoint: `DELETE /tenants/me/admins/{admin_user_id}` (requires mayorista JWT)
- List admins endpoint: `GET /tenants/me/admins`

## Dependencies

### Requires
- 006-invite-admin-to-tenant
- 009-jwt-session-management (refresh token denylist)

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Admin has no active refresh tokens at revocation | Revocation still succeeds; no denylist entries needed |
| Mayorista accidentally revokes themselves | Prevented: `403` if `admin_user_id` matches the requesting user |
| Revoked admin's access token used within 15-min window | Accepted risk; token expires naturally |

## Out of Scope

- Permanent user deletion (future intent)
- Audit log of revocation events (future intent)
