---
id: 049-openai-generation-ui
unit: 004-openai-generation-ui
intent: 008-openai-image-generation
type: simple-construction-bolt
status: planned
stories:
  - 001-generation-form
  - 002-generation-review
  - 003-product-integration-ui
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 047-product-generation-bridge
  - 048-product-publication-sync
requires_units: []
enables_bolts: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 3
---

# Bolt: 049-openai-generation-ui

## Overview

Build the staff-facing generation, review, recomposition and publication experience.

## Objective

Expose all supported workflows from Virtual Closet and the BFashion product context without client-side provider access.

## Stories Included

- **001-generation-form**: Generation form (Must)
- **002-generation-review**: Generation review (Must)
- **003-product-integration-ui**: Product integration UI (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → frontend UI and BFashion entry surface
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 047-product-generation-bridge, 048-product-publication-sync

### Enables
- None

## Success Criteria

- [ ] Staff can submit, monitor, preview, recompose, select and publish.
- [ ] Non-staff users see no generation controls or private data.
- [ ] UI handles partial sync and provider errors accessibly.
