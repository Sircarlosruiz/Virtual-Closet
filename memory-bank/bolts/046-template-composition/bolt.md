---
id: 046-template-composition
unit: 002-template-composition-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: planned
stories:
  - 003-deterministic-sku-composition
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 045-template-lifecycle
enables_bolts:
  - 047-product-generation-bridge
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 046-template-composition

## Overview

Implement deterministic SKU/overlay composition after AI generation.

## Objective

Guarantee exact visible references and non-destructive recomposition without unnecessary OpenAI calls.

## Stories Included

- **003-deterministic-sku-composition**: Deterministic SKU composition (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → composition service
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- 045-template-lifecycle (Required)

### Enables
- 047-product-generation-bridge

## Success Criteria

- [ ] Exact SKU rendering and fit validation pass tests.
- [ ] Base image and prior published versions remain unchanged.
