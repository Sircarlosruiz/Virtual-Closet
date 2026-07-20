---
stage: implement
bolt: 032-multi-pose-vton-generation-ui
created: 2026-07-18T16:48:52Z
---

## Implementation Walkthrough: multi-pose-vton-generation-ui

### Summary

Built the grouped PoseSet result view with live React Query polling, per-pose
status cards, generated-image display, reconnecting state, and retry actions
through the existing batch-item retry endpoint.

### Structure Overview

The route is a thin dashboard entry point. `PoseSetResultView` owns polling and
retry state, while typed API contracts remain in `lib/api`. Backend result
responses now include `batch_id`, which is required to invoke the existing retry
route without introducing a new endpoint.

### Completed Work

- [x] `frontend/lib/api/pose-sets.ts` - typed result response and getter
- [x] `frontend/components/pose-set/PoseSetResultView.tsx` - polling, cards, status, error, retry, and reconnecting UI
- [x] `frontend/app/(dashboard)/pose-sets/[poseSetId]/page.tsx` - result route
- [x] `backend/api/schemas/pose_sets.py` - exposes batch ID in detail response
- [x] `backend/services/pose_set_service.py` - includes batch ID in projection

### Key Decisions

- **React Query interval**: polling runs every three seconds until every item is complete or failed.
- **Last-known state**: network errors retain existing data and show a reconnecting banner.
- **Existing retry contract**: failed cards call `/api/batches/{batch_id}/items/{item_id}/retry` directly.

### Deviations from Plan

- Added `batch_id` to the backend PoseSet detail response because the existing retry endpoint requires it.

### Dependencies Added

- [x] None

### Developer Notes

The route intentionally handles 404 separately from transient polling errors.
Catalog integration remains out of scope.
