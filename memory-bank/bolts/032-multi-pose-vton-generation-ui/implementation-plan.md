---
stage: plan
bolt: 032-multi-pose-vton-generation-ui
created: 2026-07-18T16:48:52Z
---

## Implementation Plan: multi-pose-vton-generation-ui

### Objective

Build the grouped PoseSet result page at `/pose-sets/[poseSetId]`, showing one
card per selected pose, polling until terminal state, and retrying failed items
through the existing batch-item retry API.

### Deliverables

- `frontend/lib/api/pose-sets.ts` — typed result response and getter
- `frontend/lib/api/batches.ts` — reuse existing `retryBatchItem`
- `frontend/components/pose-set/PoseSetResultView.tsx` — polling/result UI
- `frontend/app/(dashboard)/pose-sets/[poseSetId]/page.tsx` — route
- `test-walkthrough.md`

### Dependencies

- `GET /api/pose-sets/{id}` from bolt 030
- Existing `POST /api/batches/{batch_id}/items/{item_id}/retry`
- React Query already used by `BatchProgressPage`
- Existing Card, Badge, Button, Progress, and toast components

### Technical Approach

- Use React Query `refetchInterval` at 3 seconds while any item is pending or processing.
- Stop polling when every item is `complete` or `failed`; retain the last result snapshot on network errors and show a reconnecting label.
- Render a responsive editorial gallery: large result cards with pose label, status accent, generated image when available, and error/retry treatment.
- Retry mutation optimistically changes the selected item to pending, calls the existing batch endpoint using `batch_id` + `batch_item_id`, then invalidates the PoseSet query.
- Treat API 404 as a not-found state, not a generic network error.

### Acceptance Criteria

- [ ] One card renders for every selected pose
- [ ] Pending/processing states show clear indicators
- [ ] Completed cards show generated image
- [ ] Failed cards show error reason and Retry action
- [ ] Retry resumes polling
- [ ] Polling stops at all-terminal state
- [ ] Network errors preserve the last data and show reconnecting state
- [ ] Unowned/nonexistent PoseSet shows a 404 state
