---
id: 010-catalog-management-ui
unit: 003-catalog-management-ui
intent: 002-catalog-management
type: simple-construction-bolt
status: planned
stories:
  - 004-customer-management-page
  - 005-buyer-portal-page
created: 2026-05-28T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

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

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → implementation-walkthrough.md
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 008-customer-portal-service (customer registration + buyer portal APIs)
- 009-catalog-management-ui (buyer portal is a continuation of the UI app)

### Enables
- None (final bolt — construction complete for this intent)

## Success Criteria

- [ ] All 2 story acceptance criteria pass
- [ ] Buyer can authenticate via invitation link and browse catalogs end-to-end
- [ ] Expired token shows "Request new link" flow
- [ ] Portal is visually distinct from mayorista admin area

## Notes

- Buyer portal routes (`/portal/*`) must not render mayorista navigation
- Buyer session cookie handling distinct from mayorista JWT — separate auth context
