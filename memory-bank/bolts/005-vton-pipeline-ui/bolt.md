---
id: 005-vton-pipeline-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
type: simple-construction-bolt
status: planned
stories:
  - 004-job-status-polling-ui
  - 005-result-display-ui
  - 006-job-history-ui
created: 2026-05-26T00:00:00Z
started: null
completed: null
current_stage: null
stages_completed: []

requires_bolts:
  - 004-vton-pipeline-ui
  - 003-vton-job-service
enables_bolts: []
requires_units: []
blocks: false

complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 005-vton-pipeline-ui

## Overview

Implements the post-submission frontend: real-time job status polling with animated state transitions, before/after result display, failed job error state, and the job history list page.

## Objective

Build the `/dashboard/jobs/[id]` page (with SWR polling) and the `/dashboard/jobs` history list. Complete the full end-to-end user journey through the VTON pipeline in the UI.

## Stories Included

- **004-job-status-polling-ui**: Auto-polling with queued/processing/done/failed states (Must)
- **005-result-display-ui**: Before/after image comparison + failed state (Must)
- **006-job-history-ui**: Paginated job history list with status badges + thumbnails (Should)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Polling strategy (SWR vs. React Query), component tree for job page and history page, mobile layout plan
- [ ] **2. Implement**: `app/(dashboard)/jobs/[id]/page.tsx`, `app/(dashboard)/jobs/page.tsx`, `components/vton/JobStatusPoller.tsx`, `components/vton/ResultDisplay.tsx`, `components/vton/JobHistoryList.tsx`
- [ ] **3. Test**: Manual test full flow — submit → wait for processing → result shown; test failed state; test history pagination; test on mobile

## Dependencies

### Requires
- 004-vton-pipeline-ui (user arrives from submit page)
- 003-vton-job-service (poll and history endpoints must exist)

### Enables
- Nothing (terminal bolt for this intent)

## Success Criteria

- [ ] Polling starts automatically on page load for active jobs
- [ ] Polling stops when job reaches `completed` or `failed`
- [ ] No polling memory leak on page unmount
- [ ] Before/after layout shows correctly at 375px and 1280px
- [ ] Failed state displays error reason clearly
- [ ] Job history shows correct status badges and thumbnails
- [ ] "Load more" pagination works for history
- [ ] End-to-end happy path: generate → poll → result visible
