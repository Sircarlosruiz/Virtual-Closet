---
id: 028-model-pose-service
unit: 001-model-pose-service
intent: 006-multi-pose-vton-generation
type: ddd-construction-bolt
status: complete
stories:
  - 001-create-model
  - 002-upload-pose-photo
  - 003-list-model-poses
created: 2026-07-17T00:00:00.000Z
started: 2026-07-18T04:10:25.000Z
completed: "2026-07-18T04:53:00Z"
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-07-18T04:10:25.000Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-07-18T04:10:25.000Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-07-18T04:10:25.000Z
    artifact: adr-012-extend-model-photos-table.md, adr-013-404-for-unowned-resources.md
  - name: implement
    completed: 2026-07-18T04:10:25.000Z
    artifact: backend/models/model.py, backend/models/media.py, backend/repositories/model_repo.py, backend/repositories/media_repo.py, backend/services/model_pose_service.py, backend/services/media_service.py, backend/api/schemas/models.py, backend/api/routers/models.py, backend/main.py, alembic migration f1e2d3c4b5a6
requires_bolts: []
enables_bolts:
  - 029-model-pose-service
  - 030-pose-set-service
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 028-model-pose-service

## Overview

Establishes the core `Model`/`ModelPhoto` domain — a new `Model` aggregate owning 1..N pose-tagged `ModelPhoto` records, with CRUD and listing API.

## Objective

Implement `Model` creation, pose photo upload (with fixed enum + duplicate-type validation), and pose listing so a mayorista can build a multi-angle model.

## Stories Included

- **001-create-model**: Create Model Identity (Must)
- **002-upload-pose-photo**: Upload Pose Photo with Fixed Enum Validation (Must)
- **003-list-model-poses**: List Poses for a Model (Must)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Define `Model` entity and extend `ModelPhoto` with `model_id` FK + `pose` enum → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: `POST /api/models`, `POST /api/models/{id}/poses`, `GET /api/models/{id}/poses` endpoints, validation rules → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Django model migration, DRF serializers/ViewSets, reuse existing media upload/validation service
- [ ] **4. Test**: Unit + integration tests for duplicate-pose rejection, ownership scoping, min-1-pose invariant → `ddd-03-test-report.md`

## Dependencies

### Requires
- None (foundational bolt for this intent)
- Note: Must coordinate with existing `ModelPhoto` model from `001-media-service` (intent `001-vton-generation-pipeline`) — this is a schema extension, not a new table

### Enables
- 029-model-pose-service (backfill needs the extended schema to exist)
- 030-pose-set-service (needs to read a model's poses)

## Success Criteria

- [ ] `POST /api/models` creates a `Model` scoped to the authenticated mayorista
- [ ] Pose upload rejects a duplicate pose type on the same model with 400
- [ ] `GET /api/models/{id}/poses` returns poses ordered `front, side, back` with working presigned URLs
- [ ] Mayorista cannot access another mayorista's models/poses

## Notes

Key design decision: extend the existing `ModelPhoto` table (add `model_id` FK, `pose` enum) rather than creating a parallel table, to keep curated-library `ModelPhoto` rows in the same table with `model_id=null`.
