---
id: 044-generation-reliability
unit: 001-image-generation-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: planned
stories:
  - 003-provider-invocation-history
  - 004-retry-idempotency-limits
  - 005-usage-recording
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 043-image-generation-service
enables_bolts:
  - 047-product-generation-bridge
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 2
---

# Bolt: 044-generation-reliability

## Overview

Add provider invocation history, safe retries, idempotency, limits and usage records.

## Objective

Make platform-paid image generation durable, observable and safe against duplicate provider calls.

## Stories Included

- **003-provider-invocation-history**: Provider invocation history (Must)
- **004-retry-idempotency-limits**: Retry, idempotency and limits (Must)
- **005-usage-recording**: Usage recording (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → backend reliability layer
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- 043-image-generation-service (Required)

### Enables
- 047-product-generation-bridge

## Success Criteria

- [ ] Duplicate, timeout, 429 and restart scenarios are tested.
- [ ] Usage unknown is distinct from zero.
- [ ] No secret reaches logs or persisted provider metadata.
