---
unit: 002-tenant-account-service
intent: 006-user-authentication-accounts
phase: inception
status: draft
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
---

# Unit Brief: Tenant Account Service

## Purpose

Foundational multi-tenancy layer for Virtual Closet. Introduces the `Tenant` model and `tenant_id` foreign key across the platform, enforces cross-tenant data isolation via ORM-level middleware, manages admin sub-roles within mayorista tenants, and generates signed buyer catalog access links.

## Scope

### In Scope
- `Tenant` entity: create, read, update (name/settings), soft-delete
- Alembic migration introducing `tenant_id` column on all platform tables (`media`, `catalogs`, `vton_jobs`, `batch_jobs`, etc.)
- Tenant isolation middleware: injects `tenant_id` filter into all DB queries from JWT claims
- Admin sub-role: invite by email (fresh registration within tenant), list admins, revoke admin access + session invalidation
- Buyer signed-link generation: catalog-scoped JWT signed with per-tenant secret, 30-day TTL (configurable)
- Buyer link validation endpoint (stateless token check)

### Out of Scope
- User authentication, login, 2FA → `001-auth-service`
- Frontend pages → `003-auth-accounts-ui`
- Subscription tiers / plan management (future intent)
- Billing or payment (future intent)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-5 | Admin sub-role — invite (fresh registration), list, revoke | Should |
| FR-6 | Buyer catalog access via signed JWT link (30-day, catalog-scoped, stateless) | Must |
| FR-7 | Multi-tenant data isolation — `tenant_id` on all records, 404 on cross-tenant access | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Attributes |
|--------|-------------|------------|
| `Tenant` | A mayorista's isolated account/organization | `id` (UUID), `name`, `slug`, `buyer_link_secret`, `settings` (JSONB), `created_at`, `is_active` |
| `AdminInvitation` | Pending admin invitation | `id`, `tenant_id`, `email`, `token`, `expires_at`, `accepted` |
| `BuyerLink` | Issued signed catalog access link | `id`, `tenant_id`, `catalog_ids[]`, `token_jti`, `expires_at`, `created_by` |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| `create_tenant` | Bootstrap a new tenant on mayorista registration | mayorista user_id, business_name | tenant |
| `get_tenant` | Fetch tenant details | tenant_id | tenant |
| `invite_admin` | Send invitation email to new admin (fresh registration) | tenant_id, invitee_email | invitation, email sent |
| `accept_invitation` | Register new user within tenant via invitation token | token, email, password | user (admin role) |
| `list_admins` | List all admin users in a tenant | tenant_id | user[] |
| `revoke_admin` | Remove admin role + invalidate sessions | tenant_id, admin_user_id | success |
| `generate_buyer_link` | Create signed JWT for catalog access | tenant_id, catalog_ids[], ttl_days | signed_url |
| `validate_buyer_link` | Verify buyer JWT, return accessible catalog_ids | token | catalog_ids[] or 403 |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 7 |
| Must Have | 5 |
| Should Have | 2 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority |
|----------|-------|----------|
| 001 | Create and Manage Tenant | Must |
| 002 | Tenant Isolation Middleware | Must |
| 003 | Cross-Tenant Access Returns 404 | Must |
| 004 | Generate Buyer Catalog Access Link | Must |
| 005 | Validate Buyer Catalog Access Link | Must |
| 006 | Invite Admin to Tenant | Should |
| 007 | Revoke Admin Access | Should |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| None | Foundational unit — no internal dependencies |

### Depended By
| Unit | Reason |
|------|--------|
| `001-auth-service` | Tenant lookup on user registration and login |
| `003-auth-accounts-ui` | Admin invite UI, buyer link generation UI |
| All platform services | `tenant_id` middleware; isolation enforced here |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| PostgreSQL | Tenant data + migrations backfilling `tenant_id` | Low |
| Email Service (SES/SendGrid) | Admin invitation emails | Medium |

---

## Technical Context

### Suggested Technology
- FastAPI + SQLAlchemy (async) — consistent with existing backend
- Alembic for multi-step migration (add tenants table → backfill `tenant_id` → add FK constraints)
- `python-jose` HS256 for buyer link signing (per-tenant secret stored on `Tenant.buyer_link_secret`)
- Middleware as FastAPI dependency injected into all routers

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| All platform services | Middleware injection | FastAPI dependency |
| Email Service | Outbound | REST API |

### Data Storage
| Data | Type | Volume | Retention |
|------|------|--------|-----------|
| Tenants | PostgreSQL | Low (< 100k) | Permanent |
| Admin invitations | PostgreSQL | Very low | 7-day TTL |
| Buyer links (audit) | PostgreSQL | Medium | Permanent (audit trail) |

---

## Constraints

- **CRITICAL**: The Alembic migration must be a multi-step transaction: (1) create `tenants` table, (2) add nullable `tenant_id` columns, (3) backfill existing rows with a default tenant, (4) add NOT NULL constraint + FK. Backfill is required for all platform tables with existing data.
- Cross-tenant access must return 404, not 403, to prevent tenant enumeration
- Per-tenant `buyer_link_secret` must be a random 32-byte hex string generated at tenant creation; stored encrypted or as an env-backed secret
- Admin invitations expire in 7 days; expired tokens return a clear error
- `002-tenant-account-service` must be deployed BEFORE `001-auth-service` (dependency)

---

## Success Criteria

### Functional
- [ ] Tenant is created automatically on mayorista registration
- [ ] All existing platform records are migrated with a valid `tenant_id`
- [ ] A mayorista cannot access another mayorista's resources (returns 404)
- [ ] Buyer link grants access only to specified catalogs; expired links return clear error
- [ ] Admin invitation flow: email sent → fresh registration → admin role granted

### Non-Functional
- [ ] Tenant isolation middleware adds < 5ms to request latency (p95)
- [ ] Buyer link validation < 150ms (p95) — stateless, no DB call for validation
- [ ] Backfill migration completes in < 60s on current data volume

### Quality
- [ ] Integration tests verify cross-tenant isolation for media, catalogs, vton_jobs, batch_jobs
- [ ] Code coverage > 80%
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| bolt-1 | ddd-construction-bolt | S001, S002, S003 | Tenant model + migration + isolation middleware |
| bolt-2 | ddd-construction-bolt | S004, S005, S006, S007 | Buyer links + admin invite/revoke |

---

## Notes

- The `tenant_id` backfill migration is the highest-risk operation in this intent — run in a transaction with a rollback plan
- Buyer link validation is intentionally stateless (no DB lookup on validation) for performance; the `BuyerLink` table is an audit trail only
- Consider Postgres RLS as defense-in-depth layer alongside ORM-level filtering
