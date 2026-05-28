---
id: 010-catalog-management-ui
unit: 003-catalog-management-ui
intent: 002-catalog-management
type: simple-construction-bolt
status: complete
stories:
  - 004-customer-management-page
  - 005-buyer-portal-page
created: 2026-05-28T00:00:00Z
started: 2026-05-28T21:30:00Z
completed: 2026-05-28T22:30:00Z
current_stage: test
stages_completed:
  - name: plan
    completed: 2026-05-28T21:30:00Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-05-28T22:00:00Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-05-28T22:30:00Z
    artifact: test-walkthrough.md

requires_bolts:
  - 008-customer-portal-service
  - 009-catalog-management-ui
enables_bolts: []
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 1
---

# Bolt: 010-catalog-management-ui

## Overview

Second frontend bolt — customer management page for the mayorista and the buyer portal experience for registered customers.

## Objective

Build the customer registration UI (mayorista registers buyers) and the buyer-facing portal where authenticated customers browse published catalogs.

## Stories Included

- **004-customer-management-page**: Mayorista registers and views customers (Must)
- **005-buyer-portal-page**: Buyer authenticates via link and browses catalogs (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [x] **1. plan**: Complete → implementation-plan.md
- [x] **2. implement**: Complete → implementation-walkthrough.md
- [x] **3. test**: Complete → test-walkthrough.md

## Dependencies

### Requires
- 008-customer-portal-service (customer registration + buyer portal APIs)
- 009-catalog-management-ui (buyer portal is a continuation of the UI app)

### Enables
- None (final bolt — construction complete for this intent)

## Success Criteria

- [x] All 2 story acceptance criteria pass
- [x] Buyer can authenticate via invitation link and browse catalogs end-to-end
- [x] Expired token shows "Request new link" flow
- [x] Portal is visually distinct from mayorista admin area

## Notes

- Buyer portal routes (`/portal/*`) must not render mayorista navigation
- Buyer session cookie handling distinct from mayorista JWT — separate auth context
