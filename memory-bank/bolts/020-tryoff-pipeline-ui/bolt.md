---
id: 020-tryoff-pipeline-ui
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
type: simple-construction-bolt
status: complete
stories:
  - 004-extracted-garment-gallery
  - 005-vton-handoff-action
created: 2026-05-31T00:00:00.000Z
started: 2026-06-01T14:35:00.000Z
completed: "2026-06-01T14:58:06Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-01T14:40:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-01T14:50:00.000Z
    artifact: implementation-walkthrough.md
requires_bolts:
  - 018-tryoff-job-service
  - 019-tryoff-pipeline-ui
enables_bolts: []
requires_units: []
blocks: false
complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 020-tryoff-pipeline-ui

## Overview

Media library integration and VTON handoff. Adds extracted garment filtering to the media library and the "Use in VTON" one-click navigation action to close the TryOff → VTON loop.

## Objective

Deliver the extracted garments gallery filter in the media library and the "Use in VTON ↗" button that pre-fills the VTON submission form with the selected garment.

## Stories Included

- **004-extracted-garment-gallery**: Media library filter for extracted garments (Must)
- **005-vton-handoff-action**: "Use in VTON" button with pre-filled navigation (Should)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Implementation Plan**: Media library filter integration; "Use in VTON" button placement (status page + gallery); VTON page query param contract
- [ ] **2. Implementation**: Gallery filter + detail panel + "Use in VTON" button + router.push with `?garment_id`
- [ ] **3. Review & Test**: Manual test: extracted garment appears in gallery; clicking "Use in VTON" pre-fills VTON form

## Dependencies

### Requires
- 018-tryoff-job-service (GET /media?type=extracted_garment must work)
- 019-tryoff-pipeline-ui (status page must be complete; "Use in VTON" button also appears there)

### Enables
- Nothing — this is the final bolt for this intent

## Success Criteria

- [ ] "Extracted Garments" filter in media library shows only extracted garment items
- [ ] Each item shows garment type badge and extraction date
- [ ] Clicking "Use in VTON" on any extracted garment navigates to `/vton/new?garment_id=<id>`
- [ ] Empty state shown when no extracted garments exist

## Notes

- VTON submission page (`/vton/new`) must read `?garment_id` query param — coordinate with intent 001 frontend
- "Use in VTON" button appears in: (1) job card on status page when complete, (2) media gallery item detail panel
- Garment type badge uses existing design system badge variants
