---
id: 029-model-pose-service
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
type: ddd-construction-bolt
status: complete
stories:
  - 004-backfill-legacy-models
created: 2026-07-17T00:00:00.000Z
started: 2026-07-18T05:12:30.000Z
completed: "2026-07-18T06:44:08Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-07-18T05:12:30.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-07-18T05:12:30.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-07-18T05:12:30.000Z
    artifact: adr-041-noop-downgrade-data-migrations.md, adr-042-batched-autocommit-data-migrations.md
  - name: implement
    completed: 2026-07-18T05:26:38.000Z
    artifact: b7c8d9e0f1a2_backfill_legacy_model_photos.py
requires_bolts:
  - 028-model-pose-service
enables_bolts:
  - 030-pose-set-service
requires_units: []
blocks: true
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 029-model-pose-service

## Overview

One-time data migration wrapping every pre-existing, non-curated `ModelPhoto` row into an implicit single-pose `Model`, preserving backward compatibility for mayoristas who never adopt multi-pose.

## Objective

Guarantee zero data loss and unchanged behavior for legacy model photos after the `Model`/`ModelPhoto` schema change lands in 028.

## Stories Included

- **004-backfill-legacy-models**: Backfill Legacy ModelPhoto Rows into Models (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Confirm backfill invariants (idempotency, curated exclusion) against 028's schema → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: Django data migration strategy, batching approach for large tables → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Data migration script
- [ ] **4. Test**: Migration tests — idempotency, curated-row exclusion, row-count parity before/after → `ddd-03-test-report.md`

## Dependencies

### Requires
- 028-model-pose-service (needs the extended `ModelPhoto` schema and `Model` table to exist)

### Enables
- 030-pose-set-service (submission flow assumes every mayorista-owned `ModelPhoto` has a `Model` parent)

## Success Criteria

- [ ] Every non-curated `ModelPhoto` row has a non-null `model_id` after migration
- [ ] Every backfilled `Model` has exactly 1 pose (`front`)
- [ ] Curated `ModelPhoto` rows are untouched
- [ ] Migration is safely re-runnable (no duplicate `Model` creation on re-run)

## Notes

Run as a Django data migration, not a management command, so it's applied automatically as part of deployment.
