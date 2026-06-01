---
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
phase: inception
status: draft
unit_type: frontend
default_bolt_type: simple-construction-bolt
created: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:00:00Z
---

# Unit Brief: tryoff-pipeline-ui

## Purpose

Next.js frontend pages and components for the TryOff garment extraction flow. Allows mayoristas to upload source images, select which garments to extract, monitor job progress, view results in the media gallery, and hand off extracted garments to the VTON pipeline in one click.

## Scope

### In Scope
- Source image upload page (drag-and-drop, file picker)
- Garment type selector UI (upper / lower / dress chips — can select multiple)
- Multi-job submission (one API call per garment type)
- Extraction job status display (polling, progress indicators)
- Extracted garment gallery integrated into the existing media library UI
- "Use in VTON" one-click handoff button on each extracted garment
- TryOff job history page

### Out of Scope
- Backend API logic (owned by 002-tryoff-job-service)
- VTON job creation itself — handoff navigates to existing VTON submission with garment pre-filled
- Authentication / layout — reuses existing app shell

---

## Assigned Requirements

| FR | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Source image upload UI (lifestyle and product photos) | Must |
| FR-2 | Garment type selector — multiple garments from same image | Must |
| FR-3 | Async job status display (polling) | Must |
| FR-4 | Show extracted garment output on completion | Must |
| FR-5 | Display extracted garments in media library | Must |
| FR-6 | One-click VTON handoff with garment pre-filled | Must |
| FR-8 | TryOff job history page | Should |

---

## Domain Concepts

### Key Entities
| Entity | Description | Attributes |
|--------|-------------|------------|
| TryoffJobCard | UI representation of a single extraction job | job_id, garment_type, status, thumbnail, created_at |
| GarmentSelector | Multi-select UI control | selected garment types (upper / lower / dress) |
| ExtractionResult | Completed job with output image | job_id, output_url, garment_type, source_image_thumb |

### Key Operations
| Operation | Description | Inputs | Outputs |
|-----------|-------------|--------|---------|
| Upload + Submit | Upload source image, select garments, submit jobs | image file, garment types[] | Job cards with status |
| Poll status | Auto-refresh job status until complete | job_id | Updated job card (thumbnail on done) |
| VTON handoff | Navigate to VTON flow with extracted garment pre-filled | extracted garment media item | VTON submission page pre-filled |
| History view | Show list of past extractions | none | TryoffJobCard[] |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 5 |
| Must Have | 4 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-source-image-upload-page | Source image upload page | Must | Planned |
| 002-garment-type-selector | Garment type multi-selector | Must | Planned |
| 003-extraction-status-display | Extraction job status display | Must | Planned |
| 004-extracted-garment-gallery | Extracted garments in media library | Must | Planned |
| 005-vton-handoff-action | One-click VTON handoff | Should | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| 002-tryoff-job-service | All API endpoints consumed here |
| 001-vton-generation-pipeline / vton-pipeline-ui | VTON submission flow navigation target |

### External Dependencies
| System | Purpose | Risk |
|--------|---------|------|
| Existing media library UI | Integrate extracted garments into existing gallery | Low |

---

## Technical Context

### Suggested Technology
- Next.js 16 App Router (existing frontend stack)
- React Server Components + Client Components per existing patterns
- shadcn/ui for upload dropzone, chips, progress indicators
- SWR or React Query for job status polling
- Tailwind CSS (existing design system)

### Integration Points
| Integration | Type | Protocol |
|-------------|------|----------|
| 002-tryoff-job-service | API calls | REST/HTTPS |
| Existing VTON submission page | Navigation (router.push with query params) | Next.js routing |

---

## Constraints

- Must reuse existing auth session (no new login flow)
- Garment type selector must map to `upper / lower / dress` values — do not expose FLUX prompts to UI
- "Use in VTON" navigates to existing VTON page with `?garment_id=<media_id>` query param

---

## Success Criteria

### Functional
- [ ] Mayorista can upload an image, select 2 garment types, and submit — resulting in 2 queued jobs
- [ ] Job status updates automatically (no manual refresh needed)
- [ ] Extracted garment appears in media library with garment type tag on completion
- [ ] "Use in VTON" button pre-fills garment field in VTON submission form

### Non-Functional
- [ ] Upload page renders in < 2 seconds
- [ ] Status polling interval ≤ 5 seconds (no aggressive polling)

### Quality
- [ ] All acceptance criteria met
- [ ] Tested in browser (golden path + edge cases)

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| 019-tryoff-pipeline-ui | simple-construction-bolt | 001, 002, 003 | Upload page + garment selector + job status |
| 020-tryoff-pipeline-ui | simple-construction-bolt | 004, 005 | Media gallery integration + VTON handoff |

---

## Notes

- Job status polling should use exponential backoff: 2s → 4s → 8s → 10s cap
- Source image preview should display immediately after selection (before upload) for UX
- Extracted garments tagged as `type: extracted_garment` in media library — filter existing gallery to show them
