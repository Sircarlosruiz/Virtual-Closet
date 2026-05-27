---
id: 003-job-submission-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: draft
priority: must
created: 2026-05-26T00:00:00Z
assigned_bolt: 004-vton-pipeline-ui
implemented: false
---

# Story: 003-job-submission-ui

## User Story

**As a** mayorista
**I want** to select the cloth type and submit the VTON generation job
**So that** the AI pipeline starts processing my garment

## Acceptance Criteria

- [ ] **Given** garment and model are selected, **When** I view the submission section, **Then** I see a cloth type selector with three options: Upper Body, Lower Body, Dress
- [ ] **Given** no cloth type is selected, **When** I view the Generate button, **Then** it is disabled
- [ ] **Given** garment, model, and cloth type are all selected, **When** I view the Generate button, **Then** it is enabled and shows "Generate try-on"
- [ ] **Given** I click Generate, **When** the API call to `POST /api/vton/generate` is in progress, **Then** the button shows a loading spinner and is disabled
- [ ] **Given** the job submission succeeds, **When** the response returns `job_id`, **Then** I am redirected to `/dashboard/jobs/{job_id}` to see the job status
- [ ] **Given** the API returns an error, **When** submission fails, **Then** an error toast is shown and the form remains, ready to retry

## Technical Notes

- Component: `ClothTypeSelector` using shadcn/ui `RadioGroup` or segmented tabs
- Cloth type values: `upper_body`, `lower_body`, `dress` (match API enum exactly)
- Display labels: "Upper Body", "Lower Body", "Dress"
- Generate button disabled states: missing garment | missing model | missing cloth_type | submitting
- Redirect via Next.js `router.push` after successful response

## Dependencies

### Requires
- `002-model-selection-ui` (model must be selected first)

### Enables
- `003-vton-pipeline-ui/004-job-status-polling-ui` (redirects to job status page)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User double-clicks Generate | Second click ignored (button disabled during submission) |
| Session expired before submission | API returns 401; show "Session expired, please log in" toast |

## Out of Scope

- Selecting multiple cloth types per job
- Preview of expected output before generating
