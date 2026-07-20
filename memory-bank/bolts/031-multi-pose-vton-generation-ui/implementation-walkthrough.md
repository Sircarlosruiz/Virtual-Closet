---
stage: implement
bolt: 031-multi-pose-vton-generation-ui
created: 2026-07-18T16:48:52Z
---

## Implementation Walkthrough: multi-pose-vton-generation-ui

### Summary

Built a responsive model/pose management page and integrated named-model pose
selection into the existing generation flow. Single-pose and curated model
selection continue through the existing VTON endpoint; multi-pose selections use
the PoseSet endpoint and redirect with its returned ID.

### Structure Overview

The frontend keeps REST contracts in `lib/api`, management UI in a dedicated
`model-pose` component area, and the existing generate page as the orchestration
surface. The backend gained the minimal owned-model listing endpoint required by
the new UI.

### Completed Work

- [x] `frontend/lib/api/model-poses.ts` - typed Model and pose CRUD client
- [x] `frontend/lib/api/pose-sets.ts` - typed PoseSet submission client
- [x] `frontend/components/model-pose/ModelPoseManagement.tsx` - create, list, upload, and pose availability UI
- [x] `frontend/components/model-pose/ModelPosePicker.tsx` - named model and legacy/curated model selection
- [x] `frontend/components/model-pose/PoseSelection.tsx` - all-selected pose cards with minimum-one state
- [x] `frontend/app/(dashboard)/models/page.tsx` - model management route
- [x] `frontend/app/(dashboard)/generate/page.tsx` - legacy branching and multi-pose redirect flow
- [x] `backend/repositories/model_repo.py` - owned model listing
- [x] `backend/services/model_pose_service.py` - model count listing
- [x] `backend/api/schemas/models.py` - model list response DTOs
- [x] `backend/api/routers/models.py` - `GET /api/models`

### Key Decisions

- **Legacy branch preserved**: one-pose named models and curated individual photos continue using `/api/vton/generate`.
- **Multi-pose branch**: models with more than one pose default to all selected and submit `/api/pose-sets`.
- **Used pose types remain visible**: management cards show occupied slots and only offer upload for unused types.

### Deviations from Plan

- Added `GET /api/models` to complete the frontend contract; the backend from bolt 028 did not yet expose named-model listing.
- Full-stack lint still reports unrelated pre-existing frontend errors; all changed files have zero errors and only existing `<img>` optimization warnings.

### Dependencies Added

- [x] None

### Developer Notes

The UI uses the existing cookie-aware `apiFetch`, shadcn primitives, and
dashboard route group. Pose-set result rendering is intentionally deferred to
bolt 032.
