---
id: 006-catalog-service
unit: 001-catalog-service
intent: 002-catalog-management
type: ddd-construction-bolt
status: complete
stories:
  - 001-create-catalog
  - 002-add-catalog-item
  - 003-remove-catalog-item
  - 004-reorder-catalog-items
created: 2026-05-28T00:00:00.000Z
started: 2026-05-28T10:00:00.000Z
completed: "2026-05-28T17:04:07Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-05-28T10:30:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-05-28T11:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-05-28T11:15:00.000Z
    artifact: null
  - name: implement
    completed: 2026-05-28T12:00:00.000Z
    artifact: src/catalogo/
  - name: test
    completed: 2026-05-28T13:00:00.000Z
    artifact: ddd-03-test-report.md
requires_bolts: []
enables_bolts:
  - 007-catalog-service
  - 009-catalog-management-ui
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 006-catalog-service

## Overview

First bolt for the catalog service — establishes the core domain model (Catalog + CatalogItem entities) and implements the foundational item CRUD operations.

## Objective

Implement catalog creation and item lifecycle management: create a catalog, add VTON results as items with metadata, remove items, and reorder items within a catalog.

## Stories Included

- **001-create-catalog**: Create named catalog with draft status (Must)
- **002-add-catalog-item**: Add completed VTON result as catalog item with metadata (Must)
- **003-remove-catalog-item**: Remove an item from a catalog (Must)
- **004-reorder-catalog-items**: Reorder items within a catalog atomically (Must)

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
- None (first bolt for this intent)

### Enables
- 007-catalog-service (catalog lifecycle operations)
- 009-catalog-management-ui (catalog management UI depends on these APIs)

## Success Criteria

- [ ] Catalog and CatalogItem models defined with proper row-level isolation
- [ ] All 4 story acceptance criteria pass
- [ ] Mayorista cannot access another mayorista's catalogs or items
- [ ] Tests passing

## Notes

- `image_key` (not URL) stored in DB; pre-signed URLs generated on demand via MinIO SDK
- `position` maintained as integer; reorder is atomic DB transaction
- Cross-reference VTON job ownership: validate job belongs to same mayorista before adding item
