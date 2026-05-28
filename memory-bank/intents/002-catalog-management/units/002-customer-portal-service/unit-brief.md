---
unit: 002-customer-portal-service
intent: 002-catalog-management
phase: inception
status: complete
created: 2026-05-28T00:00:00.000Z
updated: 2026-05-28T00:00:00.000Z
default_bolt_type: ddd-construction-bolt
---

# Unit Brief: 002-customer-portal-service

## Purpose

Manages the buyer/customer domain: mayoristas register customers (buyers), customers authenticate via invitation or magic-link tokens, and authenticated customers browse the published catalogs from their associated mayorista.

## Scope

### In Scope
- Mayorista registers a customer (name + email), scoped to that mayorista
- Invitation email sent with a signed access token
- Customer authenticates via invitation link or magic-link login
- Buyer session cookie issued after successful token validation
- Customer browses list of published catalogs from their mayorista
- Customer views full catalog detail (items in mayorista-defined order)

### Out of Scope
- Catalog creation or management (handled by 001-catalog-service)
- Mayorista authentication (platform JWT — not built here)
- Frontend rendering (handled by 003-catalog-management-ui)
- Customer can modify or comment on catalog items

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-9 | Customer registration — `POST /api/customers` with `{name, email}`, sends invite | Must |
| FR-10 | Buyer portal auth — token validation → buyer session cookie; magic-link re-request | Must |
| FR-11 | Browse published catalogs — `GET /api/portal/catalogs` and `GET /api/portal/catalogs/{id}` | Must |

---

## Domain Concepts

### Key Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| `Customer` | A buyer registered under a mayorista | `id, mayorista_id, name, email, status (invited/active), invitation_token_hash, token_expires_at, created_at` |
| `BuyerSession` | Active buyer portal session | Managed via signed session cookie (JWT or opaque token) |

### Key Operations

| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| RegisterCustomer | Create customer, hash token, send invite email | `mayorista_id, name, email` | `Customer` (status: invited) |
| ValidateToken | Check token hash + expiry, issue buyer session | `token` (from URL) | Buyer session cookie |
| RequestMagicLink | Re-send new signed token to customer email | `email` | 204 (email sent) |
| ListPortalCatalogs | Return published catalogs for buyer's mayorista | `buyer_mayorista_id, page` | `Catalog[]` |
| GetPortalCatalog | Return catalog detail with items (mayorista order) | `catalog_id, buyer_mayorista_id` | `Catalog` + `CatalogItem[]` |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 3 |
| Must Have | 3 |
| Should Have | 0 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-register-customer | Register Buyer / Customer | Must | Planned |
| 002-buyer-portal-auth | Buyer Portal Authentication | Must | Planned |
| 003-browse-published-catalogs | Browse Published Catalogs | Must | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-catalog-service` | Reads published `Catalog` and `CatalogItem` records for portal browsing |

### Depended By

| Unit | Reason |
|------|--------|
| `003-catalog-management-ui` | Consumes customer registration and buyer portal APIs |

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| PostgreSQL | Persists Customer records | Low |
| Email Service (SMTP/SendGrid) | Delivers invitation and magic-link emails | Medium — abstract behind service interface |
| MinIO | Pre-signed URLs for item images in portal | Low (via 001-catalog-service read path) |

---

## Technical Context

### Suggested Technology
- Django REST Framework
- PyJWT for signed invitation / magic-link tokens
- Email abstraction: Django `send_mail` with `EMAIL_BACKEND` env var (SMTP in prod, console in dev)

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| 001-catalog-service (read) | Internal DB | Django ORM cross-app query |
| Email service | Outbound | Django email backend |

### Data Storage

| Data | Type | Notes |
|------|------|-------|
| Customer records | PostgreSQL | `customer` table, mayorista-scoped |
| Invitation token | PostgreSQL | Stored as hash (never plaintext) |

---

## Constraints

- Customer email must be unique per mayorista (not globally)
- Invitation tokens are stored as hashes — plaintext sent only in email link, never persisted
- Token TTL: 7 days for invitation, 15 minutes for magic-link
- Buyer can only access published catalogs from their own mayorista
- Draft catalogs return 404 to buyer (not 403, to avoid revealing existence)

---

## Success Criteria

### Functional
- [ ] All 3 story acceptance criteria pass
- [ ] Buyer cannot access draft catalogs (404)
- [ ] Buyer cannot access another mayorista's catalogs (403 on direct ID access)

### Non-Functional
- [ ] Portal catalog detail p95 < 500ms

### Quality
- [ ] Code coverage > 80%
- [ ] Token security: no plaintext storage, expiry enforced
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 008-customer-portal-service | ddd-construction-bolt | 001, 002, 003 | Full customer + buyer portal domain |
