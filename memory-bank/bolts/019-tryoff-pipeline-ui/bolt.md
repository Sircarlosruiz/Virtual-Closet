---
id: 019-tryoff-pipeline-ui
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
type: simple-construction-bolt
status: complete
stories:
  - 001-source-image-upload-page
  - 002-garment-type-selector
  - 003-extraction-status-display
created: 2026-05-31T00:00:00.000Z
started: 2026-06-01T00:00:00.000Z
completed: "2026-06-01T14:34:13Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-01T00:00:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-01T00:00:00.000Z
    artifact: implementation-walkthrough.md
requires_bolts:
  - 017-tryoff-job-service
enables_bolts:
  - 020-tryoff-pipeline-ui
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 019-tryoff-pipeline-ui

## Overview

Core TryOff UI flow: upload page, garment type selector, and job status display. Covers the complete submission-to-result journey for the extraction pipeline.

## Objective

Deliver the end-to-end UI: mayorista uploads a source image, selects garment types, submits the batch, and sees live status updates per job with thumbnails on completion.

## Stories Included

- **001-source-image-upload-page**: `/tryoff/new` — drag-and-drop source image upload (Must)
- **002-garment-type-selector**: Garment type chips + batch submit (Must)
- **003-extraction-status-display**: Live status polling per job card (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Implementation Plan**: Route structure (`/tryoff/new`, `/tryoff/status`); component map; API integration points; polling strategy
- [ ] **2. Implementation**: Pages + components + API calls + polling logic
- [ ] **3. Review & Test**: Manual browser test of golden path (upload → select → submit → status → complete)

## Dependencies

### Requires
- 017-tryoff-job-service (POST /jobs/batch + GET /jobs/{id} must be live)

### Enables
- 020-tryoff-pipeline-ui (gallery and handoff depend on status page completion)

## Success Criteria

- [ ] Mayorista can upload image, select 2 garment types, submit, and see 2 job cards with live status
- [ ] Job cards update without page refresh
- [ ] Completed job card shows extracted garment thumbnail
- [ ] Failed job card shows error message

## Notes

- Polling uses SWR with exponential backoff (2s → 10s cap); stops when all jobs terminal
- shadcn/ui components: Dropzone, Toggle/Badge for garment chips, Card, Skeleton
- Source image preview uses `URL.createObjectURL` (no server round-trip before submit)
