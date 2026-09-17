---
id: 043-image-generation-service
unit: 001-image-generation-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: planned
stories:
  - 001-staff-provider-selection
  - 002-staff-generation-jobs
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
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

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → backend generation service
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- None

### Enables
- 044-generation-reliability, 045-template-lifecycle

## Success Criteria

- [ ] Provider and job boundaries are documented.
- [ ] Staff authorization and secret handling are tested.
- [ ] Four generation modes have validated queue contracts.
