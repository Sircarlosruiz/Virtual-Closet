---
id: 008-customer-portal-service
unit: 002-customer-portal-service
intent: 002-catalog-management
type: ddd-construction-bolt
status: planned
stories:
  - 001-register-customer
  - 002-buyer-portal-auth
  - 003-browse-published-catalogs
created: 2026-05-28T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 007-catalog-service
enables_bolts:
  - 010-catalog-management-ui
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 008-customer-portal-service

## Overview

Full customer portal domain: mayorista registers buyers, buyers authenticate via signed invitation/magic-link tokens, and authenticated buyers browse published catalogs.

## Objective

Implement the Customer entity, invitation token flow, buyer session management, and read-only portal catalog browsing — all with strict mayorista-scoped isolation.

## Stories Included

- **001-register-customer**: Mayorista registers buyer (name, email) → invitation email (Must)
- **002-buyer-portal-auth**: Buyer validates token → buyer session cookie; magic-link re-request (Must)
- **003-browse-published-catalogs**: Buyer browses published catalogs from their mayorista (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → src/customer_portal/
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- 007-catalog-service (published Catalog + CatalogItem data needed for portal browsing)

### Enables
- 010-catalog-management-ui (customer management page + buyer portal UI)

## Success Criteria

- [ ] All 3 story acceptance criteria pass
- [ ] Invitation tokens stored as hashes — plaintext never in DB
- [ ] Buyer session cookie does NOT grant access to mayorista admin endpoints
- [ ] Buyer cannot access draft catalogs (404) or another mayorista's catalogs (403)
- [ ] Magic-link endpoint does not enumerate registered emails (always 200)
- [ ] Tests passing

## Notes

- Higher uncertainty (2) due to token security and email delivery abstraction
- Abstract email sending behind a service interface — `console.log` in dev, SMTP/SendGrid in prod via `EMAIL_BACKEND` env var
- Buyer portal routes share `/api/portal/` prefix, distinct from mayorista `/api/` routes
