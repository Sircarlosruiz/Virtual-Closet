---
id: 044-generation-reliability
unit: 001-image-generation-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: complete
stories:
  - 003-provider-invocation-history
  - 004-retry-idempotency-limits
  - 005-usage-recording
created: 2026-09-17T01:23:26.000Z
started: 2026-09-17T16:45:00.000Z
completed: "2026-09-17T22:19:52Z"
current_stage: null
stages_completed:
  - name: model
    completed: 2026-09-17T16:50:00.000Z
    artifact: ddd-01-domain-model.md
  - name: design
    completed: 2026-09-17T17:00:00.000Z
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: 2026-09-17T17:10:00.000Z
    artifact: adr-049-manual-retry-on-timeout.md, adr-050-postgres-lease-over-redis.md
  - name: implement
    completed: 2026-09-17T19:00:00.000Z
    artifact: backend reliability layer (models, repos, services, router, worker)
  - name: test
    completed: 2026-09-17T21:55:00.000Z
    artifact: ddd-03-test-report.md
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

- [x] **1. model**: Complete → ddd-01-domain-model.md
- [x] **2. design**: Complete → ddd-02-technical-design.md
- [x] **2b. ADR Analysis**: Complete → adr-049, adr-050
- [x] **3. implement**: Complete → backend reliability layer
- [x] **4. test**: Complete → ddd-03-test-report.md

## Dependencies

### Requires
- 043-image-generation-service (Required)

### Enables
- 047-product-generation-bridge

## Success Criteria

- [ ] Duplicate, timeout, 429 and restart scenarios are tested.
- [ ] Usage unknown is distinct from zero.
- [ ] No secret reaches logs or persisted provider metadata.
