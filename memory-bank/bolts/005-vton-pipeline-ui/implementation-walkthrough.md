---
stage: implement
bolt: 005-vton-pipeline-ui
created: 2026-05-27T00:35:00Z
---

## Implementation Walkthrough: 005-vton-pipeline-ui

### Summary

Built the post-submission frontend completing the full VTON user journey: job status page with React Query auto-polling, result display with before/after comparison, failed error state, and paginated job history list.

### Structure Overview

Pages under `app/(dashboard)/jobs/` with reusable vton components. Polling uses React Query's `refetchInterval` with automatic disabling on terminal states (completed/failed).

### Completed Work

- [x] `components/vton/JobStatusPoller.tsx` — React Query polling hook (`useJobPolling`) with 5s interval, auto-disables on completed/failed; `JobStatusPoller` UI component with status indicators (queued/processing/completed/failed), loading skeleton, error state with retry
- [x] `components/vton/ResultDisplay.tsx` — Before/after side-by-side layout (stacked on mobile via `grid-cols-1 md:grid-cols-2`), result image with loading skeleton, failed state with Alert + error reason, "Generate another" button, "Try again" button for failures
- [x] `components/vton/JobHistoryList.tsx` — Paginated list fetching `GET /api/vton/jobs`, status badges (gray/blue/green/red), result thumbnails for completed jobs, cloth type labels in Spanish, "Load more" button, empty state with "Generate your first try-on" CTA, each row links to `/dashboard/jobs/{id}`
- [x] `app/(dashboard)/jobs/[id]/page.tsx` — Job status page using `useJobPolling` hook, conditional rendering based on job state, back button to history, ResultDisplay shown on completion/failure
- [x] `app/(dashboard)/jobs/page.tsx` — Job history list page with header and JobHistoryList component
- [x] `components/ui/alert.tsx` — shadcn/ui Alert component (newly installed)

### Key Decisions

- **React Query `refetchInterval` callback**: Uses functional form to check current query data status — returns `false` to stop polling on terminal states
- **No garment URL in result**: Backend `get_job_status` doesn't return garment presigned URL — ResultDisplay shows "Imagen no disponible" for the "before" side (can be enhanced later)
- **Ref for prevStatus tracking**: Used `useRef` instead of `useState` in useEffect to avoid React lint warning about setState in effects
- **Spanish date formatting**: `toLocaleDateString("es-NI")` for localized date display
- **Pagination**: "Load more" button (not infinite scroll) for simplicity and accessibility

### Deviations from Plan

None — implementation follows the plan exactly.

### Dependencies Added

- [x] `alert` — shadcn/ui Alert component for failed state display

### Developer Notes

- `useJobPolling` hook is exported separately for reuse in the job status page
- Job status page uses both `JobStatusPoller` (for status UI) and `useJobPolling` (for data access) — could be consolidated later
- History list fetches all items on initial load with `page_size=20`, "Load more" appends next page
- Status badge colors match spec: queued (secondary/gray), processing (outline), completed (default/green), failed (destructive/red)
