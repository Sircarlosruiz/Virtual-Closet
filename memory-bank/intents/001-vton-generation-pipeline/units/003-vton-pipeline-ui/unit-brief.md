---
unit: 003-vton-pipeline-ui
unit_type: frontend
default_bolt_type: simple-construction-bolt
intent: 001-vton-generation-pipeline
phase: inception
status: draft
created: 2026-05-26T00:00:00Z
updated: 2026-05-26T00:00:00Z
---

# Unit Brief: 003-vton-pipeline-ui

## Purpose

Provides all user-facing screens and interactions for the VTON pipeline: uploading garment and model photos, selecting model from the curated library or own uploads, choosing cloth type, submitting generation jobs, monitoring job status in real time via polling, viewing generated results, and browsing job history.

## Scope

### In Scope
- Garment photo upload form with preview
- Model photo selection (own uploads tab + curated library tab)
- Own model photo upload within the selection flow
- Cloth type selector (upper body / lower body / dress)
- Job submission button with loading/disabled state
- Job status screen with polling: queued → processing → done / failed states
- Result display: before/after comparison (garment vs. generated image)
- Job history list with status and result thumbnails

### Out of Scope
- Catalog creation from results (separate intent)
- WhatsApp sharing (separate intent)
- Admin UI for managing the curated model library

---

## Assigned Requirements

All user-facing FRs from the intent, expressed as UI interactions:

| FR | UI Expression | Priority |
|----|--------------|----------|
| FR-1 | Garment upload form | Must |
| FR-2 | Model selection UI (own + curated) | Must |
| FR-3 | Cloth type selector | Must |
| FR-4 | Job submission form + confirmation | Must |
| FR-5 | Status polling with progress UI | Must |
| FR-6 | Status display + result image | Must |
| FR-7 | Failed state display with retry option | Must |
| FR-8 | Job history page | Should |

---

## Domain Concepts

### Key Components

| Component | Description |
|-----------|-------------|
| `GarmentUploader` | File input with drag-and-drop, preview, validation feedback |
| `ModelSelector` | Tabbed panel: "My Models" (own uploads) + "Model Library" (curated) |
| `ClothTypeSelector` | Radio/segmented control for `upper_body`, `lower_body`, `dress` |
| `GenerateButton` | Submit button with disabled state until all inputs selected |
| `JobStatusPoller` | Polls `GET /api/vton/jobs/{id}` every N seconds, updates UI |
| `ResultDisplay` | Before/after image comparison when job completes |
| `JobHistoryList` | Paginated list of past jobs with status badges and thumbnails |

### Key Pages / Routes

| Route | Purpose |
|-------|---------|
| `/dashboard/generate` | Main VTON generation flow |
| `/dashboard/jobs` | Job history list |
| `/dashboard/jobs/[id]` | Individual job status and result |

---

## Story Summary

| Metric | Count |
|--------|-------|
| Total Stories | 6 |
| Must Have | 5 |
| Should Have | 1 |
| Could Have | 0 |

### Stories

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| 001-garment-upload-ui | Garment Upload Form | Must | Planned |
| 002-model-selection-ui | Model Selection UI | Must | Planned |
| 003-job-submission-ui | Job Submission Form | Must | Planned |
| 004-job-status-polling-ui | Job Status Polling UI | Must | Planned |
| 005-result-display-ui | Result Display | Must | Planned |
| 006-job-history-ui | Job History Page | Should | Planned |

---

## Dependencies

### Depends On
| Unit | Reason |
|------|--------|
| `001-media-service` | Upload endpoints (`POST /api/media/garments`, `POST /api/media/models`, `GET /api/media/models/curated`) |
| `002-vton-job-service` | Job endpoints (`POST /api/vton/generate`, `GET /api/vton/jobs/{id}`, `GET /api/vton/jobs`) |

### Depended By
| Unit | Reason |
|------|--------|
| None | Terminal unit for this intent |

---

## Technical Context

### Suggested Technology
- Next.js 14 App Router pages under `app/(dashboard)/generate/` and `app/(dashboard)/jobs/`
- Components in `components/vton/` (`GarmentUploader`, `ModelSelector`, `ClothTypeSelector`, `JobStatusPoller`, `ResultDisplay`)
- SWR or React Query for polling `GET /api/vton/jobs/{id}` every 5 seconds
- shadcn/ui: `Tabs`, `RadioGroup`, `Button`, `Dialog`, `Badge`, `Skeleton`
- Tailwind CSS for layout and responsive design

### Integration Points

| Integration | Type | Protocol |
|-------------|------|----------|
| Backend API | REST | fetch / axios, JSON |

---

## Constraints

- Polling interval: every 5 seconds while job is `queued` or `processing`; stop on `completed` or `failed`
- Mobile-first layout: upload flow must work on phone (mayoristas often use mobile)
- WCAG AA: all interactive elements must be keyboard accessible
- Images shown via short-lived pre-signed URLs — do not cache beyond expiry

---

## Success Criteria

### Functional
- [ ] Mayorista can upload garment photo with live preview
- [ ] Mayorista can select own model or curated library model
- [ ] Cloth type selector works and is required before submission
- [ ] Job status updates automatically via polling (no manual refresh)
- [ ] Generated image displayed when job completes
- [ ] Failed job shows error state with clear message
- [ ] Job history shows past jobs with status and results

### Non-Functional
- [ ] Upload form usable on mobile (375px viewport)
- [ ] WCAG AA compliance on all interactive elements
- [ ] Status polling does not block UI or cause layout shifts

---

## Bolt Suggestions

| Bolt | Type | Stories | Objective |
|------|------|---------|-----------|
| `004-vton-pipeline-ui` | simple-construction-bolt | 001, 002, 003 | Upload + model selection + job submission |
| `005-vton-pipeline-ui` | simple-construction-bolt | 004, 005, 006 | Status polling + result display + history |
