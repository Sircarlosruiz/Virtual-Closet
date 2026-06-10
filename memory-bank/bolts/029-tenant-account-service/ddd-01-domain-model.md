---
stage: domain-model
bolt: 029-tenant-account-service
created: 2026-06-09T19:30:00Z
---

## Static Model: 029-tenant-account-service (Buyer Links + Admin Management)

### Context

This bolt extends the domain model established in bolt 028 (028-tenant-account-service), which defined the core `Tenant`, `AdminInvitation`, and `BuyerLink` entities. This bolt focuses on the **operational flows** for buyer link generation/validation and admin sub-role lifecycle (invite, list, revoke).

### Entities (Extending Bolt 028)

- **BuyerLink** (from 028, extended): `id` (UUID, PK), `tenant_id` (UUID, FK → Tenant), `catalog_ids` (UUID array), `token_jti` (string, unique), `expires_at` (timestamp), `created_at` (timestamp), `created_by` (UUID, FK → User) — Business Rules: audit trail only (validation is stateless per ADR-014); catalog_ids must be non-empty and belong to the tenant; default TTL is 30 days; max TTL capped at 365 days; token_jti is the JWT's unique identifier for audit correlation.

- **AdminInvitation** (from 028, extended): `id` (UUID, PK), `tenant_id` (UUID, FK → Tenant), `email` (string), `token` (string, unique), `expires_at` (timestamp), `accepted` (boolean), `created_at` (timestamp), `created_by` (UUID, FK → User) — Business Rules: token is a 64-byte hex string, bcrypt-hashed before storage (per ADR-002); expires after 7 days; one pending invitation per email per tenant; accepted invitations cannot be reused; max 10 pending invitations per tenant.

- **User** (existing, extended): `id` (UUID, PK), `tenant_id` (UUID, FK → Tenant), `email` (string), `role` (string: "mayorista" | "admin" | "revoked"), `created_at` (timestamp) — Business Rules: role transitions: `admin` → `revoked` on revocation; `revoked` is terminal; mayorista role cannot be revoked.

### Value Objects

- **BuyerLinkToken**: JWT payload structure — `{ sub: "buyer", tenant_id: UUID, catalog_ids: UUID[], jti: string, iat: timestamp, exp: timestamp, type: "buyer" }`. Signed with HS256 using `Tenant.buyer_link_secret`. Constraints: `catalog_ids` must be non-empty; `exp` - `iat` ≤ 365 days; `jti` is unique per generated link.

- **BuyerLinkUrl**: Composed URL — `{FRONTEND_URL}/catalog/access?token={jwt}`. Constraints: frontend URL is environment-configured; token is the raw JWT string.

- **InvitationToken**: Secure random 64-byte hex string for admin invitation acceptance. Constraints: single-use, 7-day TTL, bcrypt-hashed before storage (per ADR-002).

- **CatalogScope**: List of catalog UUIDs defining buyer access scope. Constraints: non-empty array, all IDs must exist and belong to the tenant, duplicates removed.

- **RevocationRecord**: Tracks revoked admin session JTIs for Redis denylist — `{ jti: string, expires_at: timestamp }`. Constraints: added to Redis with TTL matching the original refresh token's remaining TTL; used to reject token refresh attempts.

### Aggregates

- **BuyerLink Aggregate**: Root: `BuyerLink` — Members: BuyerLink — Invariants: link must reference active tenant; catalog_ids must belong to the tenant; token_jti must be unique; validation is stateless (no DB lookup per ADR-014).

- **AdminInvitation Aggregate**: Root: `AdminInvitation` — Members: AdminInvitation, User (created on acceptance) — Invariants: tenant must be active to create invitations; one pending invitation per email per tenant; invitation cannot be accepted after expiration; accepted flag is immutable once true.

- **Tenant Admin Aggregate**: Root: `Tenant` — Members: Tenant, User (admins) — Invariants: mayorista role cannot be revoked; revoked users cannot access tenant resources; at least one mayorista must exist per tenant.

### Domain Events

- **BuyerLinkGenerated**: Trigger: signed link created for catalog access — Payload: `{link_id, tenant_id, catalog_ids[], expires_at, created_by, jti}`
- **BuyerLinkValidated**: Trigger: buyer link token verified (stateless) — Payload: `{tenant_id, catalog_ids[], valid: boolean, reason?: string}`
- **AdminInvitationSent**: Trigger: invitation created and email dispatched — Payload: `{invitation_id, tenant_id, email, expires_at, created_by}`
- **AdminInvitationAccepted**: Trigger: user registers via invitation token — Payload: `{invitation_id, tenant_id, user_id, email}`
- **AdminInvitationExpired**: Trigger: invitation past expires_at without acceptance — Payload: `{invitation_id, tenant_id, email}`
- **AdminRevoked**: Trigger: admin access revoked by mayorista — Payload: `{tenant_id, revoked_admin_user_id, revoked_by, session_count_invalidated}`

### Domain Services

- **BuyerLinkService**: Operations: `generate_link(tenant_id, catalog_ids, ttl_days, created_by)`, `validate_link(token)`, `list_links(tenant_id)` — Dependencies: BuyerLinkRepository, TenantRepository, JwtSigner
  - `generate_link`: Validates catalog ownership, generates JWT with HS256 + tenant secret, creates BuyerLink audit record, returns signed URL
  - `validate_link`: Two-step stateless validation — (1) decode without verification to extract `tenant_id`, (2) fetch `buyer_link_secret` from DB, (3) verify signature and return catalog_ids or error
  - `list_links`: Returns all links for tenant with expiry and catalog scope

- **AdminInvitationService**: Operations: `invite_admin(tenant_id, email, created_by)`, `accept_invitation(token, email, password)`, `list_admins(tenant_id)`, `revoke_admin(tenant_id, admin_user_id, revoked_by)` — Dependencies: AdminInvitationRepository, UserRepository, TenantRepository, EmailService, SessionService, EventPublisher
  - `invite_admin`: Checks pending invitation limit (max 10), verifies email not already admin, creates invitation with hashed token, sends email
  - `accept_invitation`: Verifies token (unexpired, not accepted), creates User with role=admin and tenant_id, marks invitation accepted
  - `list_admins`: Returns all active admins (role=admin) in tenant
  - `revoke_admin`: Sets user.role = "revoked", invalidates all refresh tokens, adds active JTIs to Redis denylist, prevents self-revoke and mayorista revocation

### Repository Interfaces

- **BuyerLinkRepository**: Entity: BuyerLink — Methods: `create(link)`, `get_by_jti(jti)`, `list_by_tenant(tenant_id)`, `list_by_tenant_with_filters(tenant_id, expired?, created_by?)`

- **AdminInvitationRepository**: Entity: AdminInvitation — Methods: `create(invitation)`, `get_by_token(token)`, `get_pending_by_email_and_tenant(email, tenant_id)`, `count_pending_by_tenant(tenant_id)`, `mark_accepted(invitation_id)`, `list_by_tenant(tenant_id)`

- **UserRepository** (extended): Entity: User — Methods: `get_admins_by_tenant(tenant_id)`, `get_by_email_and_tenant(email, tenant_id)`, `update_role(user_id, new_role)`, `get_active_refresh_token_jtis(user_id)`

### Ubiquitous Language

- **Buyer Link**: A signed JWT granting stateless, catalog-scoped access to a tenant's catalog. No account required. Validation is stateless (no DB lookup) per ADR-014.

- **Catalog Scope**: The set of catalogs a buyer link grants access to. Defined at link generation time.

- **Admin Sub-role**: A user with administrative privileges within a tenant, distinct from the tenant owner (mayorista). All admins have full access.

- **Invitation Token**: A secure, single-use token sent via email to invite a new admin. Expires in 7 days.

- **Revocation**: The process of removing an admin's access by setting their role to "revoked" and invalidating all active sessions. Access tokens (15-min TTL) cannot be immediately revoked — accepted risk.

- **Stateless Validation**: Buyer link verification that does not require a database lookup during the validation step. The `BuyerLink` table serves as an audit trail only.

- **Session Invalidation**: The process of adding active refresh token JTIs to a Redis denylist to prevent token refresh after admin revocation.
