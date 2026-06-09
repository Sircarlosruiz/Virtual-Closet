---
id: 035-auth-accounts-ui
unit: 003-auth-accounts-ui
intent: 006-user-authentication-accounts
type: simple-construction-bolt
status: planned
stories:
  - 006-buyer-catalog-access-page
  - 008-account-settings-admin-buyer-links
created: 2026-06-08T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [034-auth-accounts-ui, 029-tenant-account-service]
enables_bolts: []
requires_units: []
blocks: true

complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 035-auth-accounts-ui

### Objective

Implement the buyer catalog access page (stateless token validation → catalog view, no account required) and the account settings pages (admin management, buyer link generation).

### Stories Included

- [ ] **006-buyer-catalog-access-page**: Buyer Link Landing Page (token validation → catalog view) — Priority: Must
- [ ] **008-account-settings-admin-buyer-links**: Account Settings — Admin List/Invite/Revoke + Buyer Link Generator — Priority: Should

### Expected Outputs

- `/catalog/access` page (public, validates buyer JWT, shows accessible catalogs)
- `/settings/account` page (business name edit, 2FA method display, admin list + invite/revoke)
- `/settings/buyer-links` page (catalog multi-select, TTL input, link history table, copy button)
- Expired/invalid link error states with contact-mayorista messaging
- Confirmation dialog for admin revocation

### Dependencies

#### Bolt Dependencies (within intent)
- **034-auth-accounts-ui** (Required): Full auth flow complete (login → 2FA → session)
- **029-tenant-account-service** (Required): Buyer link + admin API endpoints must exist

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- None (final bolt in this intent)
