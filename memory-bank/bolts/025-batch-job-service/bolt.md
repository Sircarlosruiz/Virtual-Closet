---
id: 025-batch-job-service
unit: 001-batch-job-service
intent: 005-batch-vton-generation
type: ddd-construction-bolt
status: complete
started: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
current_stage: null
stages_completed:
  - name: domain-model
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-02-technical-design.md
  - name: adr-analysis
    completed: 2026-06-04T00:00:00Z
    artifact: adr-010-media-save-idempotency.md, adr-011-media-save-retry-strategy.md
  - name: implement
    completed: 2026-06-04T00:00:00Z
    artifact: services/batch_media_save_service.py, services/media_library_service.py (save_vton_result), services/batch_completion_handler.py (media save integration), repositories/batch_repo.py (set_result_media, set_media_save_error), models/batch_job.py (media_save_error), models/media.py (vton_job_id unique constraint), alembic migration update
  - name: test
    completed: 2026-06-04T00:00:00Z
    artifact: ddd-03-test-report.md

requires_bolts: [024-batch-job-service]
enables_bolts: [026-batch-vton-generation-ui]
requires_units: []
blocks: false

complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 2
---

# Bolt: 025-batch-job-service

## Overview

Adds media library auto-save on batch item completion and the batch history listing endpoint.

## Objective

When a `BatchItem` completes, its result image is automatically saved to the media library with `batch_id` / `batch_name` metadata. Mayoristas can list their batches via `GET /api/batches`.

## Stories Included

- **006-auto-save-to-media-library**: Auto-Save Completed Item to Media Library (Must)
- **007-batch-history**: Batch History API (Should)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Media item metadata schema extension for `batch_id`; batch history query patterns → `ddd-01-domain-model.md`
- [ ] **2. Technical Design**: Auto-save hook placement in completion callback; `GET /api/batches` pagination design → `ddd-02-technical-design.md`
- [ ] **3. Implement**: Extend completion callback to call media library save; `BatchListView` endpoint with pagination
- [ ] **4. Test**: Media save idempotency, cross-mayorista isolation on history endpoint → `ddd-03-test-report.md`

## Dependencies

### Requires
- 024-batch-job-service (completion callback must exist for auto-save hook)

### Enables
- 026-batch-vton-generation-ui (frontend can now consume the full API surface)

## Success Criteria

- [ ] Completed item appears in media library within 5s of job completion
- [ ] Media item includes `batch_id`, `batch_name` metadata
- [ ] MinIO failure doesn't mark item as failed (graceful degradation)
- [ ] `GET /api/batches` returns only authenticated mayorista's batches
- [ ] Pagination works correctly for large history sets

## Notes

Low complexity (1) — both stories reuse existing patterns: media save from intent 004, list endpoint from intent 002.
