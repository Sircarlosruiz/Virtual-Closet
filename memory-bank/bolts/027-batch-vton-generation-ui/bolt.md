---
id: 027-batch-vton-generation-ui
unit: 002-batch-vton-generation-ui
intent: 005-batch-vton-generation
type: simple-construction-bolt
status: complete
started: 2026-06-04T00:00:00Z
completed: 2026-06-04T00:00:00Z
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-06-04T00:00:00Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-06-04T00:00:00Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-06-04T00:00:00Z
    artifact: test-walkthrough.md

requires_bolts: [026-batch-vton-generation-ui]
enables_bolts: []
requires_units: [001-batch-job-service]
blocks: false

complexity:
  avg_complexity: 1
  avg_uncertainty: 1
  max_dependencies: 1
  testing_scope: 1
---

# Bolt: 027-batch-vton-generation-ui

## Overview

Adds the retry interaction to the progress page item rows and implements the batch history listing page.

## Objective

Mayorista can retry individual failed items from the progress page and browse all past/active batches from a history page.

## Stories Included

- **003-retry-failed-item-ui**: Retry Failed Item UI (Must)
- **004-batch-history-page**: Batch History Page (Should)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [x] **1. Plan**: Implementation plan for retry button integration and `BatchHistoryPage` → `implementation-plan.md`
- [x] **2. Implement**: Retry button with optimistic update; `BatchHistoryPage` with pagination; routing
- [x] **3. Test**: Retry double-click prevention; optimistic revert on error; empty state → `test-walkthrough.md`

## Dependencies

### Requires
- 026-batch-vton-generation-ui (`BatchProgressPage` must exist for retry button integration)

### Enables
- Nothing (final bolt for this intent)

## Success Criteria

- [x] Retry button appears only on `failed` items
- [x] Optimistic update on click; revert on API error
- [x] History page loads and paginates correctly
- [x] Empty state CTA links to batch creation flow

## Notes

Low complexity (1) — retry is a single API call with optimistic UI; history page is a standard list view.
