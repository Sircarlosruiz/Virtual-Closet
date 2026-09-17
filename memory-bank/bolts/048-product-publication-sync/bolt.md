---
id: 048-product-publication-sync
unit: 003-product-image-integration
intent: 008-openai-image-generation
type: simple-construction-bolt
status: planned
stories:
  - 002-publication-selection
  - 003-sync-delivery
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 047-product-generation-bridge
enables_bolts:
  - 049-openai-generation-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 3
---

# Bolt: 048-product-publication-sync

## Overview

Implement manual selection and idempotent publication of accepted images/configuration to Virtual Closet and BFashion products.

## Objective

Keep generation completion separate from product publication and recover partial destination failures safely.

## Stories Included

- **002-publication-selection**: Publication selection (Must)
- **003-sync-delivery**: Sync delivery (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → publication/sync adapters
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 047-product-generation-bridge

### Enables
- 049-openai-generation-ui

## Success Criteria

- [ ] Only explicitly selected results are delivered.
- [ ] Repeated delivery does not duplicate ProductImage or work.
- [ ] Per-destination status and retry are durable.
