---
id: 007-catalog-service
unit: 001-catalog-service
intent: 002-catalog-management
type: ddd-construction-bolt
status: complete
stories:
  - 005-rename-catalog
  - 006-publish-unpublish-catalog
  - 007-delete-catalog
  - 008-list-catalogs
created: 2026-05-28T00:00:00.000Z
started: 2026-05-28T14:00:00.000Z
completed: "2026-05-28T17:10:21Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-05-28T14:30:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-05-28T15:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-05-28T15:15:00.000Z
    artifact: null
  - name: implement
    completed: 2026-05-28T15:45:00.000Z
    artifact: src/catalogo/
  - name: test
    completed: 2026-05-28T16:00:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts:
  - 006-catalog-service
enables_bolts:
  - 008-customer-portal-service
  - 009-catalog-management-ui
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 007-catalog-service

## Overview

Second bolt for the catalog service — completes the catalog lifecycle with rename, publish/unpublish, delete, and list operations.

## Objective

Implement catalog lifecycle management: rename a catalog, toggle its visibility (draft ↔ published), permanently delete it, and list all of a mayorista's catalogs with pagination.

## Stories Included

- **005-rename-catalog**: Update catalog display name (Must)
- **006-publish-unpublish-catalog**: Toggle catalog status with empty-catalog guard (Must)
- **007-delete-catalog**: Permanently delete catalog and cascade items (Must)
- **008-list-catalogs**: Paginated, mayorista-scoped catalog list (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → src/catalog/
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- 006-catalog-service (Catalog + CatalogItem models must exist)

### Enables
- 008-customer-portal-service (needs published catalogs for buyer portal browsing)
- 009-catalog-management-ui (publish/unpublish and list APIs needed)

## Success Criteria

- [ ] All 4 story acceptance criteria pass
- [ ] Publish gate rejects empty catalogs (422)
- [ ] Delete cascade verified (items removed with catalog)
- [ ] Pagination tested with multiple catalogs
- [ ] Tests passing

## Notes

- PATCH endpoint handles both rename and status change — discriminate by field presence
- Published catalogs visible to buyers immediately after status change (no cache layer needed in MVP)
