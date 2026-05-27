---
id: 005-result-display-ui
unit: 003-vton-pipeline-ui
intent: 001-vton-generation-pipeline
status: draft
priority: must
created: 2026-05-26T00:00:00Z
assigned_bolt: 005-vton-pipeline-ui
implemented: false
---

# Story: 005-result-display-ui

## User Story

**As a** mayorista
**I want** to see the generated try-on image alongside the original garment photo
**So that** I can evaluate the quality and decide if it's ready for my catalog

## Acceptance Criteria

- [ ] **Given** a job transitions to `completed`, **When** polling receives the status, **Then** the result image (from `result_url`) is displayed prominently on the page
- [ ] **Given** the result is displayed, **When** I view the layout, **Then** I see a before/after comparison: original garment photo on the left, generated try-on image on the right
- [ ] **Given** the result image loads, **When** it is visible, **Then** a "Generate another" button is shown that links back to the generate page
- [ ] **Given** a job has `status=failed`, **When** the failure state is displayed, **Then** I see the error reason, a "Try again" button (goes back to generate page), and no broken image placeholder
- [ ] **Given** the result is shown, **When** I view on mobile (375px), **Then** the before/after layout stacks vertically (garment above, result below)

## Technical Notes

- Component: `ResultDisplay` in `components/vton/`
- Result image loaded from `result_url` (pre-signed URL from polling response)
- Before image: garment photo shown via its presigned URL (from form state or re-fetched from API)
- Failed state: shadcn/ui `Alert` with destructive variant + error reason text
- "Generate another" → `router.push('/dashboard/generate')`
- Image: use Next.js `<Image>` with `unoptimized` if presigned URL domain is dynamic

## Dependencies

### Requires
- `003-vton-pipeline-ui/004-job-status-polling-ui` (triggered when polling detects completion)

### Enables
- `003-vton-pipeline-ui/006-job-history-ui` (result thumbnails reuse same pattern)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Result URL expired before user views it | Next poll refreshes the URL; image reloads |
| Very large generated image (slow load) | Skeleton loader shown while image loads |
| Failed job with no error_reason | Show generic "Generation failed. Please try again." |

## Out of Scope

- Download button for generated image
- Sharing directly to WhatsApp from result page (future intent)
- Rating or feedback on result quality
