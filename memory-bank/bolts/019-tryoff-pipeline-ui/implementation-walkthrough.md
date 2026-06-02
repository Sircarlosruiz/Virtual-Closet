---
stage: implement
bolt: 019-tryoff-pipeline-ui
created: 2026-06-01T00:00:00Z
---

## Implementation Walkthrough: 003-tryoff-pipeline-ui

### Summary

Built the complete TryOff garment extraction UI flow: a source image upload page with drag-and-drop and preview, a multi-select garment type chip selector, batch job submission to the backend, and a live status page that polls job progress with exponential backoff until all jobs reach terminal states.

### Structure Overview

New `tryoff/` route group under `(dashboard)/` with two pages (new + status). Shared components live in `components/tryoff/`. API client and polling hook follow existing patterns from `lib/api/` and `hooks/`.

### Completed Work

- [x] `lib/api/tryoff.ts` — Typed API client for batch submit, single job fetch, and multi-job fetch
- [x] `hooks/use-tryoff-jobs.ts` — React Query hook polling multiple jobs with exponential backoff (2s → 10s cap), auto-stops when all terminal
- [x] `components/tryoff/image-dropzone.tsx` — Drag-and-drop zone with file validation (type + 10MB limit), immediate preview via `URL.createObjectURL`
- [x] `components/tryoff/garment-chips.tsx` — Multi-select toggle chips for upper/lower/dress garment types
- [x] `components/tryoff/job-card.tsx` — Individual job status card with state-specific UI (pending/queued/processing/complete/failed)
- [x] `components/tryoff/job-list.tsx` — Responsive grid layout for job cards with loading skeleton
- [x] `app/(dashboard)/tryoff/new/page.tsx` — Combined upload + selector page; uploads image via existing `subirPrenda`, then submits batch jobs and navigates to status
- [x] `app/(dashboard)/tryoff/status/page.tsx` — Status display page reading job IDs from query params, polling via `useTryoffJobs`, showing completion summary banner

### Key Decisions

- **Reused `subirPrenda`** from `lib/api/prendas` for image upload instead of creating a new endpoint — leverages existing multipart upload with progress tracking
- **React Query over SWR** — project already uses `@tanstack/react-query`; consistent with existing hooks like `usePrendas`
- **Combined upload + selector** on single page rather than separate steps — reduces navigation friction for the golden path
- **Job IDs via query params** (`?job_ids=id1,id2`) — simple, bookmarkable, no server-side session needed

### Deviations from Plan

- None — all deliverables implemented as planned

### Dependencies Added

- None — all packages already installed

### Developer Notes

- The `useTryoffJobs` hook sorts job IDs before building the query key to avoid duplicate queries when IDs arrive in different order
- Image dropzone reuses validation logic patterns from existing `GarmentUploader` component
- Job card shows skeleton when job is complete but thumbnail URL is not yet available (edge case for slow CDN propagation)
