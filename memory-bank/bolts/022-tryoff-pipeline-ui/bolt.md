---
id: 022-tryoff-pipeline-ui
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
type: simple-construction-bolt
status: complete
stories:
  - 007-dashboard-extraction-shortcut
created: 2026-06-03T00:00:00.000Z
started: 2026-06-03T00:00:00.000Z
completed: "2026-06-03T21:46:27Z"
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
enables_bolts: []
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 1
---

# Bolt: 022-tryoff-pipeline-ui

## Overview

Add a dashboard shortcut card that links to the garment extraction page (`/extraction/new`), making the extraction feature easily discoverable for mayoristas.

## Objective

Deliver a single dashboard card/tile with an icon, label, and description that navigates to `/extraction/new` — following the existing dashboard card styling patterns.

## Stories Included

- **007-dashboard-extraction-shortcut**: Dashboard shortcut to extraction page (Should)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Implementation Plan**: Identify dashboard page location, existing card patterns, and placement strategy
- [ ] **2. Implementation**: Add extraction shortcut card to dashboard page
- [ ] **3. Review & Test**: Verify card renders correctly, click navigates to `/extraction/new`

## Dependencies

### Requires
- 019-tryoff-pipeline-ui (dashboard page + `/extraction/new` route must exist)

### Enables
- Nothing — this is a standalone UI addition

## Success Criteria

- [ ] Extraction shortcut card visible on dashboard
- [ ] Click navigates to `/extraction/new`
- [ ] Card follows existing dashboard styling patterns
- [ ] ESLint passes, TypeScript strict mode satisfied

## Notes

- Icon: `Shirt` from lucide-react (already used in extracted-garments-grid)
- Label: "Extraer prendas"
- Description: "Extrae prendas de tus imágenes para usarlas en VTON"
