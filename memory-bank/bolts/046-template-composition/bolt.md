---
id: 046-template-composition
unit: 002-template-composition-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: complete
stories:
  - 003-deterministic-sku-composition
created: 2026-09-17T01:23:26.000Z
started: 2026-09-17T22:30:28.000Z
completed: "2026-09-18T15:14:18Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-17T22:31:28.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-17T22:32:20.000Z
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: 2026-09-17T22:44:11.000Z
    artifact: adr-053-synchronous-composition.md, adr-054-deterministic-spec-hash.md, adr-055-append-only-versions.md, adr-056-persist-blocked-compositions.md
  - name: implement
    completed: 2026-09-17T22:57:00.000Z
    artifact: product_overlay.py, composition_spec.py, sku_renderer.py, sku_composition_service.py, composition.py
  - name: test
    completed: 2026-09-17T23:15:28.000Z
    artifact: ddd-03-test-report.md
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

- [x] **1. model**: Complete → ddd-01-domain-model.md
- [x] **2. design**: Complete → ddd-02-technical-design.md
- [x] **3. adr**: Complete → adr-053-synchronous-composition.md, adr-054-deterministic-spec-hash.md, adr-055-append-only-versions.md, adr-056-persist-blocked-compositions.md
- [x] **4. implement**: Complete → composition service
- [x] **5. test**: Complete → ddd-03-test-report.md

## Dependencies

### Requires
- 045-template-lifecycle (Required)

### Enables
- 047-product-generation-bridge

## Success Criteria

- [x] Exact SKU rendering and fit validation pass tests.
- [x] Base image and prior published versions remain unchanged.
