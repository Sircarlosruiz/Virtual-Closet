---
id: 008-account-settings-admin-buyer-links
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
status: implemented
priority: should
created: 2026-06-08T00:00:00Z
assigned_bolt: 035-auth-accounts-ui
implemented: true
---

# Story: 008-account-settings-admin-buyer-links

## User Story

**As a** mayorista (account owner)
**I want** account settings pages to manage my admins and generate buyer catalog links
**So that** I can delegate access and share my catalogs with buyers

## Acceptance Criteria

- [ ] **Given** I navigate to `/settings/account`, **When** the page loads, **Then** I see: my business name (editable), my 2FA method (display-only), and a list of current admins with a "Revoke" button per admin
- [ ] **Given** I click "Invite Admin" and enter an email, **When** I submit, **Then** an invitation is sent and the pending invitation appears in the admin list with an "expires in X days" label
- [ ] **Given** I click "Revoke" on an admin, **When** I confirm the action in a dialog, **Then** the admin is removed from the list and their sessions are terminated
- [ ] **Given** I navigate to `/settings/buyer-links`, **When** the page loads, **Then** I see a form to select catalogs and TTL, plus a table of previously generated links with their expiry and catalog scope
- [ ] **Given** I select catalogs and click "Generate Link", **When** the API responds, **Then** I see the generated URL in a copyable text field with a "Copy link" button
- [ ] **Given** I am an admin (not primary owner), **When** I visit `/settings/account`, **Then** the "Invite Admin" and "Revoke" admin controls are visible (admins can manage other admins)

## Technical Notes

- Routes: `/settings/account`, `/settings/buyer-links`
- Both routes require authenticated session (auth guard applies)
- `Revoke` action shows a confirmation dialog before calling `DELETE /tenants/me/admins/{id}`
- Catalog multi-select for buyer link generation (reuse existing catalog list component if available)
- Copy button uses `navigator.clipboard.writeText()`

## Dependencies

### Requires
- 007-session-aware-routing-auth-guard
- 006-invite-admin-to-tenant (API)
- 007-revoke-admin-access (API)
- 004-generate-buyer-catalog-link (API)

### Enables
- None (leaf UI)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| No catalogs yet when generating buyer link | Empty state with link to create a catalog |
| Clipboard not available (non-HTTPS, old browser) | Fallback: show URL in a selectable text input |
| Revoking only remaining admin (self) | Prevented if user is primary owner — protected by API |

## Out of Scope

- Regenerating `buyer_link_secret` (would invalidate all existing links — future intent)
- Viewing/revoking individual buyer links before expiry
