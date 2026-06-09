---
stage: design
bolt: 028-tenant-account-service
created: 2026-06-09T00:00:00Z
---

## Technical Design: tenant-account-service

### Architecture Pattern

**Pattern**: Layered Architecture with DDD boundaries + FastAPI Dependency Injection for tenant scoping

**Rationale**: The existing backend already follows domain-driven layers (`models/`, `repositories/`, `services/`, `api/routers/`). This bolt extends that pattern with a `TenantContext` dependency that is injected at the router level, ensuring all downstream queries are automatically scoped to the current tenant's `tenant_id`.

```text
┌─────────────────────────────────────────────────────────┐
│      Presentation (API Routers)                          │  FastAPI routers with TenantContext dependency
├─────────────────────────────────────────────────────────┤
│      Application (Services)                              │  TenantService, AdminInvitationService, BuyerLinkService
├─────────────────────────────────────────────────────────┤
│        Domain (Entities + Value Objects)                 │  Tenant, AdminInvitation, BuyerLink + VOs
├─────────────────────────────────────────────────────────┤
│     Infrastructure (Repositories + DB + Middleware)      │  SQLAlchemy repos, Alembic migrations, tenant filter
└─────────────────────────────────────────────────────────┘
```

### Layer Structure

**Presentation Layer** (`api/routers/tenant.py`, `api/routers/admin.py`, `api/routers/buyer_links.py`):
- FastAPI routers with `Depends(get_tenant_context)` on every route
- Request/response schemas in `api/schemas/tenant.py`
- Error handling: domain exceptions → HTTPException translation

**Application Layer** (`services/tenant_service.py`, `services/admin_invitation_service.py`, `services/buyer_link_service.py`):
- Business logic, no FastAPI dependencies
- Raise domain exceptions (`TenantNotFoundError`, `InvitationExpiredError`, etc.)
- Publish domain events via EventPublisher

**Domain Layer** (`models/tenant.py`, `models/admin_invitation.py`, `models/buyer_link.py`):
- SQLAlchemy ORM entities
- Value objects as Python dataclasses or Pydantic models
- Domain event classes

**Infrastructure Layer** (`repositories/tenant_repo.py`, `repositories/admin_invitation_repo.py`, `repositories/buyer_link_repo.py`):
- AsyncSession-based queries
- Tenant-scoped queries via repository methods or SQLAlchemy event listeners

### Tenant Isolation Strategy

**Primary**: ORM-level query scoping via `TenantContext` FastAPI dependency

```python
# core/dependencies.py
async def get_tenant_context(
    current_user: User = Depends(get_current_mayorista),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    tenant = await tenant_repo.get_by_id(current_user.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantContext(tenant_id=tenant.id, user_id=current_user.id, role=current_user.role)
```

**Secondary**: SQLAlchemy `before_compile` event listener that auto-filters queries by `tenant_id` (defense-in-depth)

**Tertiary**: Postgres Row Level Security (RLS) — recommended as future hardening, not required for this bolt

### API Design

#### Tenant Endpoints

- **GET /tenants/me**: Returns current tenant details
  - Request: Auth cookie (JWT with tenant_id)
  - Response: `TenantResponse { id, name, slug, settings, created_at }`
  - Errors: 404 (tenant not found/inactive)

- **PATCH /tenants/me**: Update tenant name/settings
  - Request: `TenantUpdateRequest { name?, settings? }`
  - Response: `TenantResponse`
  - Errors: 404 (not found), 409 (slug conflict)

#### Admin Invitation Endpoints

- **POST /tenants/admins/invite**: Invite admin by email
  - Request: `AdminInviteRequest { email }`
  - Response: `AdminInvitationResponse { id, email, expires_at }`
  - Errors: 409 (pending invitation exists), 404 (tenant not found)

- **GET /tenants/admins**: List admins in tenant
  - Response: `AdminListResponse { admins: [AdminResponse] }`

- **DELETE /tenants/admins/{admin_id}**: Revoke admin access
  - Response: 204 No Content
  - Errors: 404 (admin not found in tenant)

- **POST /auth/accept-invitation**: Accept invitation (public endpoint)
  - Request: `AcceptInvitationRequest { token, email, password }`
  - Response: `UserResponse`
  - Errors: 400 (invalid/expired token), 409 (email already registered)

#### Buyer Link Endpoints

- **POST /tenants/buyer-links**: Generate signed catalog access link
  - Request: `BuyerLinkRequest { catalog_ids: [UUID], ttl_days? }`
  - Response: `BuyerLinkResponse { signed_url, expires_at }`
  - Errors: 400 (invalid catalog_ids), 404 (tenant not found)

- **POST /buyer-links/validate**: Validate buyer link token
  - Request: `ValidateLinkRequest { token }`
  - Response: `ValidateLinkResponse { valid, catalog_ids: [UUID], tenant_id }`
  - Errors: 403 (invalid/expired token)

### Data Model

#### New Table: `tenants`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default gen_random_uuid() |
| `name` | VARCHAR(255) | NOT NULL |
| `slug` | VARCHAR(50) | UNIQUE, NOT NULL |
| `buyer_link_secret` | VARCHAR(64) | NOT NULL, generated at creation |
| `settings` | JSONB | DEFAULT '{}' |
| `is_active` | BOOLEAN | DEFAULT true, NOT NULL |
| `created_at` | TIMESTAMPTZ | DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() |

#### New Table: `admin_invitations`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK → tenants(id), NOT NULL |
| `email` | VARCHAR(255) | NOT NULL |
| `token` | VARCHAR(128) | UNIQUE, NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `accepted` | BOOLEAN | DEFAULT false |
| `created_at` | TIMESTAMPTZ | DEFAULT now() |
| `created_by` | UUID | FK → users(id), NOT NULL |

#### New Table: `buyer_links`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK → tenants(id), NOT NULL |
| `catalog_ids` | UUID[] | NOT NULL, CHECK array_length > 0 |
| `token_jti` | VARCHAR(128) | UNIQUE, NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `created_at` | TIMESTAMPTZ | DEFAULT now() |
| `created_by` | UUID | FK → users(id), NOT NULL |

#### Migration: Add `tenant_id` to Existing Tables

**Tables to modify**: `media`, `catalogs`, `vton_jobs`, `batch_jobs`

**Multi-step migration strategy** (as per unit brief constraints):

1. **Step 1**: Create `tenants` table
2. **Step 2**: Insert default tenant for existing data (`id = '00000000-0000-0000-0000-000000000001'`, name = "Default", slug = "default")
3. **Step 3**: Add nullable `tenant_id` column to each platform table
4. **Step 4**: Backfill: `UPDATE {table} SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL`
5. **Step 5**: Add NOT NULL constraint on `tenant_id` columns
6. **Step 6**: Add FK constraints: `ALTER TABLE {table} ADD CONSTRAINT fk_{table}_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)`
7. **Step 7**: Add index on `tenant_id` for each table: `CREATE INDEX idx_{table}_tenant_id ON {table}(tenant_id)`

**Also modify `users` table**: Add `tenant_id` column (nullable initially, then NOT NULL after backfill)

### Security Design

- **Tenant Isolation**: `TenantContext` dependency injected at router level; all service methods receive `tenant_id` and scope queries accordingly
- **Cross-tenant access returns 404**: Prevents tenant enumeration; service layer checks ownership and raises `NotFoundError`
- **Buyer Link Signing**: HS256 with per-tenant `buyer_link_secret`; payload includes `tenant_id`, `catalog_ids`, `jti`, `exp`
- **Admin Invitation Tokens**: 64-byte hex, single-use, 7-day TTL; bcrypt hash stored in DB (per ADR-002)
- **JWT Claims**: `tenant_id` included in mayorista JWT; validated on every request

### NFR Implementation

- **Performance**: Tenant isolation middleware adds < 5ms latency (simple dict lookup + UUID comparison)
- **Buyer Link Validation**: Stateless JWT verification, no DB call for validation → < 150ms p95
- **Migration Safety**: All migration steps in single transaction; rollback plan documented in migration comments
- **Backfill Performance**: Batched updates with progress logging; estimated < 60s for current data volume

### Integration Points

| Integration | Direction | Protocol | Notes |
|-------------|-----------|----------|-------|
| Email Service (SES/SendGrid) | Outbound | REST API | Admin invitation emails |
| JWT Auth (`core/security.py`) | Inbound | Python import | Extract tenant_id from JWT claims |
| Existing routers | Inbound | FastAPI dependency | Add `Depends(get_tenant_context)` to all protected routes |
