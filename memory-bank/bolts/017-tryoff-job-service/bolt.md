---
id: 017-tryoff-job-service
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
type: ddd-construction-bolt
status: complete
stories:
  - 004-poll-job-status
  - 005-media-library-save
  - 006-retry-on-failure
created: 2026-05-31T00:00:00Z
started: 2026-05-31T18:30:00Z
completed: 2026-05-31T20:00:00Z
current_stage: complete
stages_completed:
  - name: domain-model
    completed: 2026-05-31T19:00:00Z
    artifact: ddd-01-domain-model.md
  - name: technical-design
    completed: 2026-05-31T19:30:00Z
    artifact: ddd-02-technical-design.md
  - name: implementation
    completed: 2026-05-31T19:45:00Z
    artifact: implementation changes
  - name: test
    completed: 2026-05-31T20:00:00Z
    artifact: ddd-03-test-report.md

requires_bolts: [016-tryoff-job-service]
enables_bolts: [018-tryoff-job-service, 019-tryoff-pipeline-ui]
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 017-tryoff-job-service

## Overview

Output handling and reliability: persist extracted garments to the media library, expose job status polling API, and wire up Celery auto-retry for transient failures.

## Objective

Complete the backend pipeline: after extraction succeeds, the garment is saved to MinIO and the media library is updated. The frontend can poll for status. Failures retry automatically up to 2 times.

## Stories Included

- **004-poll-job-status**: GET /api/tryoff/jobs/{id} — status + output URL (Must)
- **005-media-library-save**: Auto-save extracted garment to media library (Must)
- **006-retry-on-failure**: Celery auto-retry (max 2, exponential backoff) (Should)

## Bolt Type

**Type**: DDD Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/ddd-construction-bolt.md`

## Stages

- [x] **1. Domain Model**: MediaItem metadata extension (`type`, `garment_type`, `source_job_id`); retry state in TryoffJob
- [x] **2. Technical Design**: GET /jobs/{id} contract; MinIO upload path; retry decorator config; idempotency for re-uploads
- [x] **3. ADR Analysis**: Skipped - no ADR-worthy decisions identified
- [x] **4. Implementation**: Status endpoint + MinIO upload + MediaItem creation + Celery retry config
- [x] **5. Test**: Unit tests passing, integration tests verified

## Success Criteria

- [x] GET /api/tryoff/jobs/{id} returns complete status with signed output URL
- [x] Extracted garment appears in media library tagged as `extracted_garment`
- [x] Job retries on transient error; third failure sets status to `failed`
- [x] MinIO upload is idempotent (retry overwrites same key)

## Notes

- MinIO path convention: `media/{mayorista_id}/extracted/{job_id}.png`
- Signed URL TTL: 1 hour (matches existing media library)
- Celery retry: `countdown=30 * (self.request.retries + 1)` (30s, 60s)
