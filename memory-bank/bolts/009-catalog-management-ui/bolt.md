---
id: 009-catalog-management-ui
unit: 003-catalog-management-ui
intent: 002-catalog-management
type: simple-construction-bolt
status: planned
stories:
  - 001-catalog-list-page
  - 002-catalog-detail-page
  - 003-catalog-publish-flow
created: 2026-05-28T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 006-catalog-service
  - 007-catalog-service
enables_bolts:
  - 010-catalog-management-ui
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 1
---

# Bolt: 009-catalog-management-ui

## Overview

First frontend bolt — implements all mayorista-facing catalog management pages: the catalog dashboard, catalog detail with item management, and the publish/unpublish/delete flow.

## Objective

Build the mayorista's core catalog management UI: browse and create catalogs, manage items within a catalog (add from VTON results, remove, reorder), and control catalog visibility.

## Stories Included

- **001-catalog-list-page**: Catalog dashboard with create, list, and navigate (Must)
- **002-catalog-detail-page**: Catalog detail with item grid, add/remove/reorder (Must)
- **003-catalog-publish-flow**: Publish/unpublish and delete flows with confirmation (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → implementation-walkthrough.md
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 006-catalog-service (catalog CRUD + item management APIs)
- 007-catalog-service (publish/unpublish, delete, list APIs)

### Enables
- 010-catalog-management-ui (customer management + buyer portal pages)

## Success Criteria

- [ ] All 3 story acceptance criteria pass
- [ ] Mayorista can complete full catalog lifecycle end-to-end via UI
- [ ] Empty catalog publish button is disabled
- [ ] Reorder persists correctly after page refresh

## Notes

- Catalog item images load via pre-signed URLs — no client-side URL caching across page loads
- Item picker for "Add Item" queries `GET /api/vton/jobs?status=completed` (intent 001 API)
