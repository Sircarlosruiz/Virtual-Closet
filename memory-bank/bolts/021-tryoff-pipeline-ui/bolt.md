---
id: 021-tryoff-pipeline-ui
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
type: simple-construction-bolt
status: complete
stories:
  - 006-extraction-result-preview
created: 2026-06-03T00:00:00.000Z
started: 2026-06-03T00:00:00.000Z
completed: "2026-06-03T21:31:05Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-03T00:00:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-03T00:00:00.000Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-06-03T00:00:00.000Z
    artifact: test-walkthrough.md
requires_bolts:
  - 019-tryoff-pipeline-ui
  - 020-tryoff-pipeline-ui
enables_bolts: []
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 021-tryoff-pipeline-ui

## Overview

Full-size garment preview modal/lightbox for extracted garments. Provides inspection, download, and VTON handoff actions from a shared `<GarmentPreviewModal />` component usable from both the status page and media library detail panel.

## Objective

Deliver a reusable preview component that displays extracted garments at full size on their flat white background, with "Use in VTON" and "Download" actions — closing the inspection loop: extraction → preview → VTON or download.

## Stories Included

- **006-extraction-result-preview**: Extracted garment full-size preview on flat background (Should)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [x] **1. Implementation Plan**: Component architecture (`<GarmentPreviewModal />`); trigger points (status page thumbnail click, media library detail panel); download logic; presigned URL refresh strategy
- [x] **2. Implementation**: Shared modal component + integration into status page + integration into media library detail panel + download handler
- [ ] **3. Review & Test**: Manual browser test: click thumbnail → modal opens → "Use in VTON" navigates correctly → "Download" saves file → Escape closes modal

## Dependencies

### Requires
- 019-tryoff-pipeline-ui (status page with thumbnails must exist)
- 020-tryoff-pipeline-ui (media library gallery must exist)

### Enables
- Nothing — this is the final bolt for intent 004

## Success Criteria

- [ ] Clicking garment thumbnail on status page opens full-size preview modal
- [ ] Modal shows "Use in VTON" and "Download" buttons
- [ ] "Use in VTON" navigates to `/vton/new?garment_id=<media_id>`
- [ ] "Download" saves PNG with filename `extracted-<garment_type>-<job_id>.png`
- [ ] Modal closes on Escape or click outside
- [ ] Same preview component reused in media library detail panel
- [ ] Expired presigned URL handled gracefully with error toast

## Notes

- Uses existing shadcn/ui `Dialog` component
- No new API endpoints needed — image URL from job/media item object
- Presigned URL refresh on modal open if expired
- Mobile: modal uses full-screen; image scales to fit viewport
