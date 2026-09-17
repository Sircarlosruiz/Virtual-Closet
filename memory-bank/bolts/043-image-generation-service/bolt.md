---
id: 043-image-generation-service
unit: 001-image-generation-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: in_progress
stories:
  - 001-staff-provider-selection
  - 002-staff-generation-jobs
created: 2026-09-17T01:23:26Z
started: 2026-09-17T02:00:00Z
completed: null
current_stage: test
stages_completed:
  - model
  - design
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
- [ ] **3. implement**: In progress → backend generation service
- [ ] **4. test**: Blocked by missing backend dependencies → ddd-03-test-report.md

## Dependencies

### Requires
- None

### Enables
- 044-generation-reliability, 045-template-lifecycle

## Success Criteria

- [ ] Provider and job boundaries are documented.
- [ ] Staff authorization and secret handling are tested.
- [ ] Four generation modes have validated queue contracts.
