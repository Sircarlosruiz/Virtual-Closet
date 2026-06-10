---
id: 029-tenant-account-service
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
type: ddd-construction-bolt
status: complete
stories:
  - 004-generate-buyer-catalog-link
  - 005-validate-buyer-catalog-link
  - 006-invite-admin-to-tenant
  - 007-revoke-admin-access
created: 2026-06-08T00:00:00.000Z
started: 2026-06-09T19:30:00.000Z
completed: "2026-06-10T01:21:03Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-09T19:35:00.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-09T19:38:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-09T19:40:00.000Z
    artifact: adr-016-redis-denylist-session-invalidation.md, adr-017-buyer-validation-200-response.md
  - name: implement
    completed: 2026-06-09T19:50:00.000Z
    artifact: source code
  - name: test
    completed: 2026-06-09T19:55:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 028-tenant-account-service
enables_bolts:
  - 035-auth-accounts-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

## Bolt: 029-tenant-account-service

### Objective

Complete the tenant account service with buyer catalog link generation/validation and admin sub-role management (invite, list, revoke).

### Stories Included

- [ ] **004-generate-buyer-catalog-link**: Generate Buyer Catalog Access Link — Priority: Must
- [ ] **005-validate-buyer-catalog-link**: Validate Buyer Catalog Access Link (stateless) — Priority: Must
- [ ] **006-invite-admin-to-tenant**: Invite Admin to Tenant (fresh registration) — Priority: Should
- [ ] **007-revoke-admin-access**: Revoke Admin Access + Session Invalidation — Priority: Should

### Expected Outputs

- `BuyerLink` model + `AdminInvitation` model
- `POST /buyer-links`, `GET /buyer-links` endpoints
- `POST /buyer-links/validate` endpoint (stateless JWT validation)
- `POST /tenants/me/admins/invite`, `GET /tenants/me/admins`, `DELETE /tenants/me/admins/{id}` endpoints
- `POST /auth/accept-invitation` endpoint (public, token-gated)
- Unit + integration tests for all endpoints

### Dependencies

#### Bolt Dependencies (within intent)
- **028-tenant-account-service** (Required): Tenant model + `buyer_link_secret` must exist

#### Unit Dependencies (cross-unit)
- None

#### Enables (other bolts waiting on this)
- 035-auth-accounts-ui (account settings page needs admin/buyer-link APIs)
