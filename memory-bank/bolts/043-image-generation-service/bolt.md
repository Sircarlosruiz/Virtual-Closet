---
id: 043-image-generation-service
unit: 001-image-generation-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: complete
stories:
  - 001-staff-provider-selection
  - 002-staff-generation-jobs
created: '2026-09-17T01:23:26Z'
started: '2026-09-17T02:00:00Z'
completed: '2026-09-17T16:37:51Z'
current_stage: null
stages_completed:
  - name: model
    completed: '2026-09-17T02:00:00Z'
    artifact: ddd-01-domain-model.md
  - name: design
    completed: '2026-09-17T02:00:00Z'
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: '2026-09-17T04:07:47Z'
    artifact: adr-046-provider-abstraction.md, adr-047-worker-secret-boundary.md, adr-048-commit-before-enqueue.md
  - name: implement
    completed: '2026-09-17T04:07:47Z'
    artifact: backend image generation service, migration, router, and Celery task
requires_bolts: []
enables_bolts:
  - 044-generation-reliability
  - 045-template-lifecycle
requires_units: []
blocks: false
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 3
  testing_scope: 2
---

# Bolt: 043-image-generation-service

## Overview

Create the provider abstraction extension and durable staff-only generation job foundation.

## Objective

Allow supported image modes to be validated and queued while keeping OpenAI credentials server-side.

## Stories Included

- **001-staff-provider-selection**: Staff provider selection (Must)
- **002-staff-generation-jobs**: Staff generation jobs (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. model**: Complete → ddd-01-domain-model.md
- [x] **2. design**: Complete → ddd-02-technical-design.md
- [x] **3. adr**: Complete → adr-046, adr-047, adr-048
- [x] **4. implement**: Complete → backend generation service
- [x] **5. test**: Complete → ddd-03-test-report.md (pending human approval to close bolt)

## Dependencies

### Requires
- None

### Enables
- 044-generation-reliability, 045-template-lifecycle

## Success Criteria

- [x] Provider and job boundaries are documented.
- [x] Staff authorization and secret handling are tested.
- [x] Four generation modes have validated queue contracts.
