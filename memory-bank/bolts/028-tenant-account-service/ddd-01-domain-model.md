---
stage: domain-model
bolt: 028-tenant-account-service
created: 2026-06-09T00:00:00Z
---

## Static Model: tenant-account-service

### Entities

- **Tenant**: `id` (UUID, PK), `name` (string), `slug` (string, unique), `buyer_link_secret` (32-byte hex), `settings` (JSONB), `created_at` (timestamp), `updated_at` (timestamp), `is_active` (boolean) — Business Rules: slug is auto-generated from name and must be unique; buyer_link_secret is generated at creation and never changes; soft-delete via is_active flag.

- **AdminInvitation**: `id` (UUID, PK), `tenant_id` (UUID, FK → Tenant), `email` (string), `token` (string, unique), `expires_at` (timestamp), `accepted` (boolean), `created_at` (timestamp), `created_by` (UUID, FK → User) — Business Rules: token expires after 7 days; one pending invitation per email per tenant; accepted invitations cannot be reused.

- **BuyerLink**: `id` (UUID, PK), `tenant_id` (UUID, FK → Tenant), `catalog_ids` (UUID array), `token_jti` (string, unique), `expires_at` (timestamp), `created_at` (timestamp), `created_by` (UUID, FK → User) — Business Rules: audit trail only (validation is stateless); catalog_ids defines scope of access; default TTL is 30 days.

### Value Objects

- **TenantSlug**: Immutable slug derived from tenant name — lowercase, hyphenated, unique. Constraints: 3-50 chars, alphanumeric + hyphens only, no leading/trailing hyphens.

- **BuyerLinkSecret**: 32-byte random hex string used as HMAC key for buyer JWT signing. Constraints: generated once at tenant creation, never exposed in API responses.

- **InvitationToken**: Secure random token for admin invitation acceptance. Constraints: 64-byte hex, single-use, 7-day TTL.

- **CatalogScope**: List of catalog UUIDs defining buyer access scope. Constraints: non-empty array, all IDs must exist in tenant's catalogs.

### Aggregates

- **Tenant Aggregate**: Root: `Tenant` — Members: Tenant, AdminInvitation — Invariants: tenant must be active to create invitations; slug must be unique across all tenants; buyer_link_secret is immutable after creation.

- **BuyerLink Aggregate**: Root: `BuyerLink` — Members: BuyerLink — Invariants: link must reference active tenant; catalog_ids must belong to the tenant; token_jti must be unique.

### Domain Events

- **TenantCreated**: Trigger: new tenant provisioned — Payload: `{tenant_id, name, slug, created_by, timestamp}`
- **TenantDeactivated**: Trigger: tenant soft-deleted — Payload: `{tenant_id, deactivated_by, timestamp}`
- **AdminInvitationSent**: Trigger: invitation created and email dispatched — Payload: `{invitation_id, tenant_id, email, expires_at}`
- **AdminInvitationAccepted**: Trigger: user registers via invitation token — Payload: `{invitation_id, tenant_id, user_id, email}`
- **AdminInvitationExpired**: Trigger: invitation past expires_at without acceptance — Payload: `{invitation_id, tenant_id, email}`
- **BuyerLinkGenerated**: Trigger: signed link created for catalog access — Payload: `{link_id, tenant_id, catalog_ids[], expires_at, created_by}`
- **BuyerLinkValidated**: Trigger: buyer link token verified — Payload: `{link_id, tenant_id, catalog_ids[], valid: boolean}`

### Domain Services

- **TenantService**: Operations: `create_tenant`, `get_tenant`, `update_tenant`, `deactivate_tenant` — Dependencies: TenantRepository, EventPublisher
- **AdminInvitationService**: Operations: `invite_admin`, `accept_invitation`, `list_admins`, `revoke_admin` — Dependencies: AdminInvitationRepository, TenantRepository, EmailService, EventPublisher
- **BuyerLinkService**: Operations: `generate_link`, `validate_link` — Dependencies: BuyerLinkRepository, TenantRepository, JwtSigner

### Repository Interfaces

- **TenantRepository**: Entity: Tenant — Methods: `create(tenant)`, `get_by_id(id)`, `get_by_slug(slug)`, `update(tenant)`, `list_active()`, `exists_by_slug(slug)`
- **AdminInvitationRepository**: Entity: AdminInvitation — Methods: `create(invitation)`, `get_by_token(token)`, `get_pending_by_tenant(tenant_id)`, `mark_accepted(invitation_id)`, `list_by_tenant(tenant_id)`
- **BuyerLinkRepository**: Entity: BuyerLink — Methods: `create(link)`, `get_by_jti(jti)`, `list_by_tenant(tenant_id)`, `list_expired(tenant_id)`

### Ubiquitous Language

- **Tenant**: A mayorista's isolated organizational boundary; all data belongs to exactly one tenant.
- **Tenant Isolation**: The guarantee that no tenant can access another tenant's data; enforced at ORM and middleware layers.
- **Mayorista**: The wholesale business owner; each mayorista has exactly one tenant.
- **Admin Sub-role**: A user with administrative privileges within a tenant (distinct from tenant owner).
- **Buyer Link**: A signed JWT granting stateless, catalog-scoped access to a tenant's catalog.
- **Catalog Scope**: The set of catalogs a buyer link grants access to.
- **Soft-delete**: Deactivating a tenant without removing its data; preserves audit trail and prevents accidental data loss.
