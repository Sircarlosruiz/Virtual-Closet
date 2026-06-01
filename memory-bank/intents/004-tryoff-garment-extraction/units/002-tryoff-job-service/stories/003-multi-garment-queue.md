---
id: 003-multi-garment-queue
unit: 002-tryoff-job-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 016-tryoff-job-service
implemented: false
---

# Story: 003-multi-garment-queue

## User Story

**As a** mayorista
**I want** to queue extraction of multiple garments from a single source image in one request
**So that** I get separate product images for the top and pants without submitting them individually

## Acceptance Criteria

- [ ] **Given** a source image and `garment_types: ["upper", "lower"]`, **When** POST /api/tryoff/jobs/batch is called, **Then** two TryoffJob records are created (one per garment type), both enqueued, and the response lists both job IDs
- [ ] **Given** the batch is submitted, **When** one job completes and another is still processing, **Then** each job's status is tracked independently
- [ ] **Given** `garment_types` contains duplicates (e.g., `["upper", "upper"]`), **When** the batch is submitted, **Then** de-duplicated to one job per unique type
- [ ] **Given** `garment_types` is empty, **When** POST /api/tryoff/jobs/batch is called, **Then** HTTP 422 is returned

## Technical Notes

- Endpoint: `POST /api/tryoff/jobs/batch`
- Body: `{ source_image_id: uuid, garment_types: ["upper", "lower", "dress"] }`
- Creates N TryoffJob records, enqueues N Celery tasks
- Shared `source_image_id` links jobs from same session (no separate Session entity needed)
- Response: `{ jobs: [{ job_id, garment_type, status }, ...] }`

## Dependencies

### Requires
- 001-submit-tryoff-job (single job creation logic is reused)

### Enables
- 003-tryoff-pipeline-ui/002-garment-type-selector (UI sends batch request)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| All 3 garment types submitted | 3 jobs created and queued |
| Source image is flat-lay (no human) | Jobs created; extraction may produce unexpected output (validated in FASHN validation pattern) |
| One job fails, others succeed | Failed job shows `failed`; successful jobs show `complete` with outputs |

## Out of Scope

- Grouping jobs into a named "session" entity (inferred from shared source_image_id)
- Cancelling individual jobs within a batch
