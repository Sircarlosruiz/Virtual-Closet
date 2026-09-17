---
id: 047-product-generation-bridge
unit: 003-product-image-integration
intent: 008-openai-image-generation
type: simple-construction-bolt
status: planned
stories:
  - 001-product-generation-bridge
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 044-generation-reliability
  - 046-template-composition
enables_bolts:
  - 048-product-publication-sync
  - 049-openai-generation-ui
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 3
  max_dependencies: 3
  testing_scope: 3
---

# Bolt: 047-product-generation-bridge

## Overview

Define and implement the authenticated cross-application command/status bridge between BFashion and Virtual Closet.

## Objective

Allow staff to initiate from either application while Virtual Closet remains the single generation authority.

## Stories Included

- **001-product-generation-bridge**: Product generation bridge (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. plan**: Pending → implementation-plan.md
- [ ] **2. implement**: Pending → integration adapters/contracts
- [ ] **3. test**: Pending → test-walkthrough.md

## Dependencies

### Requires
- 044-generation-reliability, 046-template-composition

### Enables
- 048-product-publication-sync, 049-openai-generation-ui

## Success Criteria

- [ ] Product/wholesaler links are explicit and fail closed.
- [ ] BFashion cannot invoke OpenAI directly.
- [ ] Contract tests cover accepted and rejected requests.
