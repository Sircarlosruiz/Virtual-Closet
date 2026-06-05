---
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
phase: inception
status: ready
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
---

# Unit Brief: batch-vton-generation-ui

## Purpose

React frontend for the Batch VTON Generation feature. Provides the batch creation wizard, real-time progress monitoring page, per-item retry controls, and batch history listing.

## Scope

### In Scope
- "New Batch" creation flow: garment + model + cloth_type pairing selection UI, optional batch name, submit
- Batch detail / progress page with real-time per-item status (polling every 3s)
- Retry button on failed items in the progress view
- Batch history page listing all mayorista batches with summary counts

### Out of Scope
- Backend API logic (handled by `001-batch-job-service`)
- Individual VTON job tracking (existing `003-vton-pipeline-ui`)
- Media library management UI (existing feature)

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Batch creation UI: select pairings, name batch, submit | Must |
| FR-3 | Batch progress view: overall counters + per-item status | Must |
| FR-5 | Retry failed item from within the progress view | Must |
| FR-7 | Batch history page | Should |

---

## Domain Concepts

### Key Pages / Components

| Component | Description |
|-----------|-------------|
| `BatchCreatePage` | Multi-step wizard: select garments → pair with models → review → submit |
| `BatchProgressPage` | Live progress for an active/complete batch; polls `/api/batches/{id}` every 3s |
| `BatchItemRow` | Single item row with thumbnail, status badge, error message, and Retry button |
| `BatchHistoryPage` | Paginated list of batches with summary chips |

### Key Interactions

| Interaction | Description |
|-------------|-------------|
| Garment selection | Mayorista picks 1–100 garments from media library grid |
| Model pairing | Pair each garment with a model photo (own upload or curated library) |
| Cloth type selection | Per-item cloth type picker (upper / lower / dress) |
| Batch submit | `POST /api/batches`; redirect to `BatchProgressPage` |
| Status polling | `GET /api/batches/{id}` every 3s while batch is active |
| Retry failed | `POST /api/batches/{id}/items/{item_id}/retry`; updates row status optimistically |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 4 |
| Must Have | 3 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-batch-creation-flow | Batch Creation Flow | Must | Planned |
| 002-batch-progress-page | Batch Progress Page | Must | Planned |
| 003-retry-failed-item-ui | Retry Failed Item UI | Must | Planned |
| 004-batch-history-page | Batch History Page | Should | Planned |

---

## Dependencies

### Depends On

| Unit | Reason |
|------|--------|
| `001-batch-job-service` | All data and mutations come from this unit's REST API |

### Depended By
None — this is the leaf unit.

### External Dependencies

| System | Purpose | Risk |
|--------|---------|------|
| Media Library API | Fetch garments and model photos for pairing selection | Low — existing |

---

## Technical Context

### Suggested Technology
- React + existing component library (consistent with rest of frontend)
- Polling with `setInterval` or React Query `refetchInterval` for progress view
- Optimistic UI on retry button click

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| `001-batch-job-service` REST API | API | REST/JSON |
| Media Library API | API | REST/JSON |

---

## Constraints

- Must follow existing UX patterns (same component library and layout conventions as `003-vton-pipeline-ui`)
- Polling interval: 3s on active batch (batch status ≠ `complete`/`failed`); stop polling when terminal

---

## Success Criteria

### Functional
- [ ] Mayorista can create and submit a batch of 10–100 items
- [ ] Progress page updates in real time (≤ 3s delay)
- [ ] Failed items show error reason and a Retry button
- [ ] Retry re-enqueues item and updates row status optimistically
- [ ] Batch history lists all batches reverse-chronologically

### Non-Functional
- [ ] Batch detail page load < 300ms p95
- [ ] No stale state after retry (row reflects new `pending` status immediately)

### Quality
- [ ] Code coverage > 80%
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 026-batch-vton-generation-ui | simple-construction-bolt | 001, 002 | Batch creation wizard + progress page |
| 027-batch-vton-generation-ui | simple-construction-bolt | 003, 004 | Retry UI + batch history page |
