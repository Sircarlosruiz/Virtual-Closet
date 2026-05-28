---
id: 004-vton-pipeline-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
type: simple-construction-bolt
status: complete
stories:
  - 001-garment-upload-ui
  - 002-model-selection-ui
  - 003-job-submission-ui
created: 2026-05-26T00:00:00.000Z
started: 2026-05-27T00:00:00.000Z
completed: "2026-05-28T13:43:13Z"
current_stage: null
stages_completed:
  - name: plan
    completed: 2026-05-27T00:05:00.000Z
    artifact: implementation-plan.md
  - name: implement
    completed: 2026-05-27T00:15:00.000Z
    artifact: implementation-walkthrough.md
  - name: test
    completed: 2026-05-27T00:20:00.000Z
    artifact: test-walkthrough.md
requires_bolts:
  - 001-media-service
  - 002-vton-job-service
enables_bolts:
  - 005-vton-pipeline-ui
requires_units: []
blocks: false
complexity:
  avg_complexity: 2
  avg_uncertainty: 1
  max_dependencies: 2
  testing_scope: 2
---

# Bolt: 004-vton-pipeline-ui

## Overview

Implements the frontend upload and job submission flow: garment photo upload with preview, model photo selection (own + curated library), cloth type selector, and the Generate button that submits the job.

## Objective

Build the three-step generation form (upload garment → select model → submit) as a Next.js page with reusable shadcn/ui components. The user lands on `/dashboard/generate`, completes all steps, and is redirected to the job status page.

## Stories Included

- **001-garment-upload-ui**: Drag-and-drop garment upload with preview (Must)
- **002-model-selection-ui**: Tabbed model selector — own uploads + curated library (Must)
- **003-job-submission-ui**: Cloth type selector + Generate button + redirect on success (Must)

## Bolt Type

**Type**: Simple Construction Bolt
**Definition**: `.specsmd/aidlc/templates/construction/bolt-types/simple-construction-bolt.md`

## Stages

- [ ] **1. Plan**: Component tree, page route, API integration map, mobile layout plan
- [ ] **2. Implement**: `app/(dashboard)/generate/page.tsx`, `components/vton/GarmentUploader.tsx`, `components/vton/ModelSelector.tsx`, `components/vton/ClothTypeSelector.tsx`
- [ ] **3. Test**: Manual testing on mobile (375px) and desktop; verify all disabled states and error handling

## Dependencies

### Requires
- 001-media-service (upload endpoints + model library endpoints must exist)
- 002-vton-job-service (submit endpoint must exist)

### Enables
- 005-vton-pipeline-ui (status polling + result pages)

## Success Criteria

- [ ] Garment upload works with drag-and-drop and file picker on mobile
- [ ] Model selector shows own models and curated library in tabs
- [ ] Cloth type required before Generate button is enabled
- [ ] Successful submission redirects to `/dashboard/jobs/{job_id}`
- [ ] All error states handled (validation, API errors)
- [ ] WCAG AA: all inputs keyboard accessible
- [ ] Layout works at 375px (mobile) and 1280px (desktop)
