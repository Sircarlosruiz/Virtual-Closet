---
id: 009-catalog-management-ui
unit: 003-catalog-management-ui
intent: 002-catalog-management
type: simple-construction-bolt
status: complete
stories:
  - 001-catalog-list-page
  - 002-catalog-detail-page
  - 003-catalog-publish-flow
created: 2026-05-28T00:00:00Z
started: 2026-05-28T19:30:00Z
completed: 2026-05-28T21:00:00Z
current_stage: test
stages_completed:
  - plan
  - implement
  - test

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

- [x] **1. plan**: Complete → implementation-plan.md
- [x] **2. implement**: Complete → implementation-walkthrough.md
- [x] **3. test**: Complete → test-walkthrough.md

## Dependencies

### Requires
- 006-catalog-service (catalog CRUD + item management APIs)
- 007-catalog-service (publish/unpublish, delete, list APIs)

### Enables
- 010-catalog-management-ui (customer management + buyer portal pages)

## Success Criteria

- [x] All 3 story acceptance criteria pass
- [x] Mayorista can complete full catalog lifecycle end-to-end via UI
- [x] Empty catalog publish button is disabled
- [x] Reorder persists correctly after page refresh

## Notes

- Catalog item images load via pre-signed URLs — no client-side URL caching across page loads
- Item picker for "Add Item" queries `GET /api/vton/jobs?status=completed` (intent 001 API)
