---
stage: plan
bolt: 005-vton-pipeline-ui
created: 2026-05-27T00:30:00Z
---

## Implementation Plan: 005-vton-pipeline-ui

### Objective

Build the post-submission frontend: job status page with SWR polling, result display with before/after comparison, failed error state, and job history list page with pagination.

### Deliverables

1. **Page**: `app/(dashboard)/jobs/[id]/page.tsx` — Job status page with auto-polling, state transitions, and result display
2. **Page**: `app/(dashboard)/jobs/page.tsx` — Job history list with pagination ("Load more")
3. **Component**: `components/vton/JobStatusPoller.tsx` — SWR-based polling hook/component for `GET /api/vton/jobs/{id}`
4. **Component**: `components/vton/ResultDisplay.tsx` — Before/after image comparison + failed state
5. **Component**: `components/vton/JobHistoryList.tsx` — Paginated job history list with status badges and thumbnails

### Dependencies

- **004-vton-pipeline-ui**: User arrives from submit page redirect
- **003-vton-job-service**: Poll endpoint (`GET /api/vton/jobs/{id}`) and history endpoint (`GET /api/vton/jobs`) must exist
- **@tanstack/react-query**: Already installed in package.json — will use for polling instead of SWR (already available)
- **shadcn/ui**: `Badge`, `Button`, `Card`, `Skeleton`, `Alert` (need to install `alert`)

### API Response Schemas

**Job Status** (`GET /api/vton/jobs/{id}`):
```json
{
  "job_id": "uuid",
  "status": "queued|processing|completed|failed",
  "created_at": "datetime",
  "started_at": "datetime|null",
  "completed_at": "datetime|null",
  "result_url": "string|null",
  "error_reason": "string|null",
  "retry_count": 0
}
```

**Job History** (`GET /api/vton/jobs?page=1&page_size=20`):
```json
{
  "items": [{...VTONJobHistoryItem}],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Technical Approach

1. **Polling Strategy**: Use React Query (`@tanstack/react-query`) already installed. `refetchInterval: 5000` for active jobs, `refetchInterval: false` for completed/failed.
2. **Job Status Page**: 
   - Client component that fetches job via React Query
   - Conditional rendering based on status: queued → processing → completed/failed
   - Polling auto-stops when status reaches terminal state
3. **Result Display**:
   - Before/after side-by-side layout (stacked on mobile)
   - Garment photo URL from job response (need to fetch garment separately or include in response)
   - "Generate another" button → `/dashboard/generate`
   - Failed state: Alert component with error reason + "Try again" button
4. **Job History**:
   - Fetch `GET /api/vton/jobs?page=1&page_size=20`
   - "Load more" button appends next page
   - Status badges: queued (gray), processing (blue), completed (green), failed (red)
   - Empty state with "Generate your first try-on" button
   - Each row links to `/dashboard/jobs/{job_id}`

### Acceptance Criteria

- [ ] Polling starts automatically on page load for active jobs
- [ ] Polling stops when job reaches `completed` or `failed`
- [ ] No polling memory leak on page unmount
- [ ] Before/after layout shows correctly at 375px and 1280px
- [ ] Failed state displays error reason clearly
- [ ] Job history shows correct status badges and thumbnails
- [ ] "Load more" pagination works for history
- [ ] End-to-end happy path: generate → poll → result visible
