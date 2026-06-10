---
stage: design
bolt: 029-tenant-account-service
created: 2026-06-09T19:35:00Z
---

## Technical Design: 029-tenant-account-service (Buyer Links + Admin Management)

### Architecture Pattern

**Pattern**: Layered Architecture with DDD boundaries — consistent with bolt 028

**Rationale**: This bolt extends the tenant account service with buyer link and admin management flows. It follows the same layered pattern established in bolt 028, reusing the `TenantContext` dependency injection and tenant isolation middleware.

```text
┌─────────────────────────────────────────────────────────┐
│      Presentation (API Routers)                          │  buyer_links_router, admin_router
├─────────────────────────────────────────────────────────┤
│      Application (Services)                              │  BuyerLinkService, AdminInvitationService
├─────────────────────────────────────────────────────────┤
│        Domain (Entities + Value Objects)                 │  BuyerLink, AdminInvitation, User (extended)
├─────────────────────────────────────────────────────────┤
│     Infrastructure (Repositories + DB + Middleware)      │  SQLAlchemy repos, tenant filter, Redis denylist
└─────────────────────────────────────────────────────────┘
```

### Layer Structure

**Presentation Layer** (`api/routers/buyer_links.py`, `api/routers/admin.py`):
- FastAPI routers with `Depends(get_tenant_context)` on protected routes
- `POST /buyer-links/validate` is public (no mayorista JWT required)
- `POST /auth/accept-invitation` is public (token-gated)
- Request/response schemas in `api/schemas/buyer_links.py`, `api/schemas/admin.py`

**Application Layer** (`services/buyer_link_service.py`, `services/admin_invitation_service.py`):
- Business logic, no FastAPI dependencies
- Raise domain exceptions (`BuyerLinkError`, `InvitationExpiredError`, `AdminRevocationError`, etc.)
- Publish domain events

**Domain Layer** (models from bolt 028, extended):
- `models/buyer_link.py` — BuyerLink ORM entity
- `models/admin_invitation.py` — AdminInvitation ORM entity
- `models/user.py` — extended with role transitions

**Infrastructure Layer** (`repositories/buyer_link_repo.py`, `repositories/admin_invitation_repo.py`):
- AsyncSession-based queries
- Tenant-scoped via repository methods (tenant_id passed from TenantContext)

### API Design

#### Buyer Link Endpoints

- **POST /buyer-links**: Generate signed catalog access link
  - Auth: Mayorista JWT (via `Depends(get_tenant_context)`)
  - Request: `BuyerLinkRequest { catalog_ids: [UUID], ttl_days?: number }`
  - Response: `BuyerLinkResponse { id, signed_url, expires_at, catalog_ids: [UUID] }`
  - Errors:
    - 400: `catalog_ids` is empty or invalid
    - 404: Catalog not found or belongs to another tenant
    - 422: `ttl_days` > 365 (validation error)

- **GET /buyer-links**: List all buyer links for tenant
  - Auth: Mayorista JWT
  - Query params: `expired?: boolean`, `created_by?: UUID`
  - Response: `BuyerLinkListResponse { links: [BuyerLinkListItem], total: number }`
  - `BuyerLinkListItem { id, catalog_ids, expires_at, created_at, created_by, is_expired: boolean }`

- **POST /buyer-links/validate**: Validate buyer link token (public endpoint)
  - Auth: None (public)
  - Request: `ValidateLinkRequest { token: string }`
  - Response (200): `ValidateLinkResponse { valid: true, tenant_id: UUID, catalog_ids: [UUID] }`
  - Response (200, invalid): `ValidateLinkResponse { valid: false, reason: "link_expired" | "invalid_token" }`
  - Note: Always returns 200 — buyer has no session to refresh

#### Admin Invitation Endpoints

- **POST /tenants/me/admins/invite**: Invite admin by email
  - Auth: Mayorista JWT (must be primary account owner)
  - Request: `AdminInviteRequest { email: string }`
  - Response: `AdminInvitationResponse { id, email, expires_at }`
  - Errors:
    - 409: Pending invitation already exists for this email
    - 409: Email is already an admin in this tenant
    - 422: Max 10 pending invitations reached
    - 404: Tenant not found

- **GET /tenants/me/admins**: List active admins in tenant
  - Auth: Mayorista JWT
  - Response: `AdminListResponse { admins: [AdminResponse] }`
  - `AdminResponse { id, email, created_at }`

- **DELETE /tenants/me/admins/{admin_user_id}**: Revoke admin access
  - Auth: Mayorista JWT
  - Response: 204 No Content
  - Errors:
    - 403: Cannot revoke primary account owner (self)
    - 403: Requesting user is not mayorista
    - 404: Admin not found in tenant

#### Invitation Acceptance Endpoints (Public)

- **POST /auth/accept-invitation**: Accept invitation and register
  - Auth: None (public, token-gated)
  - Request: `AcceptInvitationRequest { token: string, email: string, password: string }`
  - Response: `UserResponse { id, email, role, tenant_id }`
  - Errors:
    - 400: Invalid or expired invitation token
    - 400: Email does not match invitation
    - 409: Email already registered on the platform

### Data Model

#### Existing Tables (from bolt 028)

- `tenants` — already created by bolt 028
- `admin_invitations` — already created by bolt 028
- `buyer_links` — already created by bolt 028

#### Migration for this Bolt

No new tables required. This bolt adds:
- **Indexes**: `idx_admin_invitations_email_tenant` on `admin_invitations(email, tenant_id)` for duplicate check
- **Indexes**: `idx_buyer_links_tenant_created` on `buyer_links(tenant_id, created_at DESC)` for listing

#### Redis Denylist Schema

For session invalidation on admin revocation:

```
Key:    denylist:{jti}
Value:  "1"
TTL:    remaining TTL of the refresh token
```

### Security Design

- **Buyer Link Signing**: HS256 with per-tenant `Tenant.buyer_link_secret` (from bolt 028)
- **Two-Step Buyer Validation** (per ADR-014):
  1. Decode JWT without verification to extract `tenant_id`
  2. Fetch `buyer_link_secret` from DB for that tenant
  3. Verify signature and check expiration
- **Admin Invitation Tokens**: 64-byte hex, bcrypt-hashed before storage (per ADR-002)
- **Self-Revocation Prevention**: Service layer checks `admin_user_id != requesting_user_id`
- **Mayorista Protection**: Cannot revoke user with `role=mayorista`
- **Cross-Tenant Isolation**: All protected endpoints use `TenantContext`; buyer validation endpoint is public but `tenant_id` is extracted from token, not from request context

### NFR Implementation

- **Buyer Link Validation**: Stateless JWT verification — no DB call during signature verification step (only one DB call to fetch `buyer_link_secret` in two-step flow) → < 150ms p95
- **Admin Invitation Rate Limit**: Max 10 pending invitations per tenant (enforced at service layer)
- **Session Invalidation**: Redis denylist lookup on token refresh — O(1) check, adds < 1ms to refresh latency
- **15-Min Revocation Window**: Accepted risk — access tokens cannot be revoked immediately; short TTL limits exposure

### Integration Points

| Integration | Direction | Protocol | Notes |
|-------------|-----------|----------|-------|
| Email Service (SES/SendGrid) | Outbound | REST API | Admin invitation emails |
| JWT Auth (`core/security.py`) | Inbound | Python import | Extract tenant_id, role from JWT |
| Redis | Inbound | RESP | Session denylist for revoked admins |
| Catalog Service | Inbound | FastAPI dependency | Validate catalog ownership before link generation |
