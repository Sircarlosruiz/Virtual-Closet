---
id: 045-template-lifecycle
unit: 002-template-composition-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: planned
stories:
  - 001-template-lifecycle
  - 002-composition-snapshot
created: 2026-09-17T01:23:26Z
started: null
completed: null
current_stage: null
stages_completed: []
requires_bolts:
  - 043-image-generation-service
enables_bolts:
  - 046-template-composition
requires_units: []
blocks: true
complexity:
  avg_complexity: 3
  avg_uncertainty: 2
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 045-template-lifecycle

## Overview

Create staff-managed common/private templates and immutable effective configuration snapshots.

## Objective

Ensure templates are reusable while historical results survive edits, archival and reference changes.

## Stories Included

- **001-template-lifecycle**: Template lifecycle (Must)
- **002-composition-snapshot**: Composition snapshot (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. model**: Pending → ddd-01-domain-model.md
- [ ] **2. design**: Pending → ddd-02-technical-design.md
- [ ] **3. implement**: Pending → template service
- [ ] **4. test**: Pending → ddd-03-test-report.md

## Dependencies

### Requires
- 043-image-generation-service (Required for result linkage)

### Enables
- 046-template-composition

## Success Criteria

- [ ] Common/private scope isolation is tested.
- [ ] Historical snapshots are immutable and durable.
- [ ] Archived templates cannot be selected for new jobs.
