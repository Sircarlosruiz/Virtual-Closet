---
id: 045-template-lifecycle
unit: 002-template-composition-service
intent: 008-openai-image-generation
type: ddd-construction-bolt
status: complete
stories:
  - 001-template-lifecycle
  - 002-composition-snapshot
created: 2026-09-17T01:23:26.000Z
started: 2026-09-17T18:31:01.000Z
completed: "2026-09-17T22:20:12Z"
current_stage: null
stages_completed:
  - name: model
    completed: "2026-09-17T18:33:22Z"
    artifact: ddd-01-domain-model.md
  - name: design
    completed: "2026-09-17T18:37:38Z"
    artifact: ddd-02-technical-design.md
  - name: adr
    completed: "2026-09-17T18:40:37Z"
    artifact: adr-051-service-layer-scope-isolation.md, adr-052-immutable-snapshot-pattern.md
  - name: implement
    completed: "2026-09-17T21:56:04Z"
    artifact: backend template lifecycle + composition snapshot service, models, migration, routers
  - name: test
    completed: "2026-09-17T22:14:40Z"
    artifact: ddd-03-test-report.md
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

- [x] **1. model**: Complete → ddd-01-domain-model.md
- [x] **2. design**: Complete → ddd-02-technical-design.md
- [x] **3. adr**: Complete → adr-051-service-layer-scope-isolation.md, adr-052-immutable-snapshot-pattern.md
- [x] **4. implement**: Complete → template lifecycle + composition snapshot service
- [x] **5. test**: Complete → ddd-03-test-report.md (pending human approval to close bolt)

## Dependencies

### Requires
- 043-image-generation-service (Required for result linkage)

### Enables
- 046-template-composition

## Success Criteria

- [ ] Common/private scope isolation is tested.
- [ ] Historical snapshots are immutable and durable.
- [ ] Archived templates cannot be selected for new jobs.
