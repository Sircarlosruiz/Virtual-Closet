---
id: 018-tryoff-job-service
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: complete
stories:
  - 007-job-history
created: 2026-05-31T00:00:00Z
started: 2026-05-31T20:05:00Z
completed: 2026-05-31T20:10:00Z
current_stage: complete
stages_completed:
  - name: domain-model
    completed: 2026-05-31T20:05:00Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-05-31T20:06:00Z
    artifact: ddd-02-technical-design.md
  - name: implementation
    completed: 2026-05-31T20:07:00Z
    artifact: already implemented in bolt 017
  - name: test
    completed: 2026-05-31T20:10:00Z
    artifact: ddd-03-test-report.md

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

- [x] **1. Domain Model**: Pagination params (page, page_size); history response shape
- [x] **2. Technical Design**: SQL query with ORDER BY + LIMIT/OFFSET; signed thumbnail URL generation
- [x] **3. Implementation**: Already implemented in bolt 017 (list_jobs endpoint + service)
- [x] **4. Test**: Verified via existing test suite

## Dependencies

### Requires
- 017-tryoff-job-service (jobs with complete status must exist)

### Enables
- 020-tryoff-pipeline-ui (history page frontend)

## Success Criteria

- [x] GET /api/tryoff/jobs returns paginated results ordered by `created_at` DESC
- [x] Thumbnail signed URL present for `complete` jobs
- [x] Empty list returns `{ items: [], total: 0 }` (not 404)
- [x] Another mayorista's jobs are never returned

## Notes

- Default page_size: 20; max: 100
- Consistent with VTON job history API pattern from intent 001
- Implementation was completed as part of bolt 017 (list_jobs method)
