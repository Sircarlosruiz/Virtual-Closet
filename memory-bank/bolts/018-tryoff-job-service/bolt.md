---
id: 018-tryoff-job-service
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: planned
stories:
  - 007-job-history
created: 2026-05-31T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts: [017-tryoff-job-service]
enables_bolts: [020-tryoff-pipeline-ui]
requires_units: []
blocks: false

complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 1
---

# Bolt: 018-tryoff-job-service

## Overview

Paginated job history API for past TryOff extractions, scoped to the authenticated mayorista.

## Objective

Deliver GET /api/tryoff/jobs with pagination so the frontend can display a history list with thumbnails and status badges.

## Stories Included

- **007-job-history**: GET /api/tryoff/jobs — paginated history list (Should)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [ ] **1. Domain Model**: Pagination params (page, page_size); history response shape
- [ ] **2. Technical Design**: SQL query with ORDER BY + LIMIT/OFFSET; signed thumbnail URL generation
- [ ] **3. Implementation**: FastAPI list endpoint + DB query + signed URL generation
- [ ] **4. Test**: Verify pagination works; verify cross-mayorista isolation; verify empty list returns correctly

## Dependencies

### Requires
- 017-tryoff-job-service (jobs with complete status must exist)

### Enables
- 020-tryoff-pipeline-ui (history page frontend)

## Success Criteria

- [ ] GET /api/tryoff/jobs returns paginated results ordered by `created_at` DESC
- [ ] Thumbnail signed URL present for `complete` jobs
- [ ] Empty list returns `{ jobs: [], total: 0 }` (not 404)
- [ ] Another mayorista's jobs are never returned

## Notes

- Default page_size: 20; max: 100
- Consistent with VTON job history API pattern from intent 001
