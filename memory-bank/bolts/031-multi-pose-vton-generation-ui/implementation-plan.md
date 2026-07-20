---
stage: plan
bolt: 031-multi-pose-vton-generation-ui
created: 2026-07-18T16:48:52Z
---

## Implementation Plan: multi-pose-vton-generation-ui

### Objective

Add a polished model/pose management surface and extend the existing generate
flow with optional pose selection, while preserving the current single-pose
VTON path for legacy models.

### Deliverables

- `frontend/lib/api/model-poses.ts` — typed Model/pose API client
- `frontend/lib/api/pose-sets.ts` — typed PoseSet submission client
- `frontend/components/model-pose/ModelPoseManagement.tsx` — model list, create flow, pose upload, availability states
- `frontend/app/(dashboard)/models/page.tsx` — model management route
- `frontend/components/vton/PoseSelection.tsx` — all-selected-by-default pose cards with minimum-one enforcement
- Update `frontend/app/(dashboard)/generate/page.tsx` — load owned Models/poses, branch legacy single-pose vs multi-pose submission, redirect to PoseSet route
- Add a small backend `GET /api/models` list endpoint if required by the UI; 028 currently exposes create/upload/list-poses but not named-model listing
- `implementation-walkthrough.md`

### Dependencies

- 028 model/pose APIs: create, upload, list poses
- 030 PoseSet API: submit selected pose IDs
- Existing `GarmentUploader`, `ClothTypeSelector`, `apiFetch`, dashboard shell, and shadcn UI primitives
- Existing `/api/media/models/mine` remains untouched for curated/single-photo compatibility

### Technical Approach

- Keep API calls in typed `lib/api` modules; preserve HttpOnly-cookie credentials through `apiFetch`.
- Use a warm editorial utility visual language: deep ink surfaces, warm ivory panels,
  coral selection accents, large pose photography, and compact status labels.
- Model management uses expandable model cards showing `pose count / 3`, a create dialog, and a pose upload panel. Used pose types render disabled rather than disappearing.
- Generate flow treats one-pose models as legacy-compatible: hide pose selection and call the existing single-pairing endpoint. For models with more than one pose, show all poses selected by default and submit `/api/pose-sets`.
- Disable submission at zero selected poses and display the selected count in the action label.
- Use accessible buttons/checkboxes, keyboard-visible focus states, responsive grids, and inline error feedback.

### Acceptance Criteria

- [ ] Existing models render with pose count and legacy one-pose models remain usable
- [ ] New model creation lands on its pose management view
- [ ] Used pose types are visibly disabled; full models show complete state
- [ ] Pose upload errors remain inline without closing the workflow
- [ ] Multi-pose selection defaults to all selected
- [ ] Submit is disabled at zero selected and shows selected count
- [ ] Multi-pose submit redirects using returned `pose_set_id`
- [ ] Single-pose model submission preserves the existing VTON behavior
- [ ] Lint/build and interaction tests pass
