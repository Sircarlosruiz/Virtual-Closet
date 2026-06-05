---
id: 001-create-batch-job
unit: 001-batch-job-service
intent: 005-batch-vton-generation
status: complete
priority: must
created: 2026-06-04T00:00:00Z
assigned_bolt: 023-batch-job-service
implemented: true
---

# Story: 001-create-batch-job

## User Story

**As a** mayorista
**I want** to submit a named list of garment+model+cloth_type pairings as a single batch
**So that** I can kick off multiple VTON generations in one action and track them together

## Acceptance Criteria

- [ ] **Given** I submit `POST /api/batches` with a valid list of 1–100 pairings and an optional name, **When** the request is received, **Then** a `BatchJob` record is created with `status: pending` and one `BatchItem` per pairing
- [ ] **Given** the batch is created, **When** the response is returned, **Then** it includes `{ batch_id, name, total_items, status: "pending" }` within 500ms
- [ ] **Given** I submit more than 100 pairings, **When** the request is processed, **Then** a `400` error is returned with `"Batch size exceeds maximum of 100 items"`
- [ ] **Given** I submit 0 pairings, **When** the request is processed, **Then** a `400` error is returned with `"Batch must contain at least 1 item"`
- [ ] **Given** the request fails mid-way (DB error), **When** the error occurs, **Then** no partial `BatchJob` or `BatchItem` records are persisted (atomic transaction)

## Technical Notes

- Use `transaction.atomic()` to wrap `BatchJob` creation + `BatchItem` bulk creation
- Validate garment_id and model_id belong to the authenticated mayorista
- `BatchJob.status` enum: `pending`, `in-progress`, `complete`, `partial` (some failed)
- Max 100 items enforced in DRF serializer `validate_items()`

## Dependencies

### Requires
- None (foundational story)

### Enables
- 002-enqueue-batch-items (needs BatchJob + BatchItems to exist)
- 003-track-item-status (needs BatchItem entity)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Garment belongs to different mayorista | 403 Forbidden on that item |
| Duplicate pairings in same batch | Allowed — two separate BatchItems |
| Name is omitted | BatchJob.name defaults to `"Batch {created_at date}"` |

## Out of Scope

- Enqueueing the VTON jobs (Story 002)
- Batch status tracking (Story 003)
