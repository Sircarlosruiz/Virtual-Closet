---
stage: plan
bolt: 019-tryoff-pipeline-ui
created: 2026-06-01T00:00:00Z
---

## Implementation Plan: 003-tryoff-pipeline-ui

### Objective

Build the core TryOff UI flow: source image upload page, garment type selector, and live job status display. Covers the complete submission-to-result journey for the garment extraction pipeline.

### Deliverables

1. **`/tryoff/new` page** — Drag-and-drop image upload with preview, file validation (type + size)
2. **Garment type selector** — Multi-select chips (upper / lower / dress) with batch submit
3. **`/tryoff/status` page** — Job cards with live polling via React Query, status badges, thumbnails on completion
4. **API client module** — `lib/api/tryoff.ts` with typed endpoints for batch submit and job polling
5. **Custom hook** — `use-tryoff-jobs.ts` for polling logic with exponential backoff

### Dependencies

- **017-tryoff-job-service**: Backend must expose `POST /api/tryoff/jobs/batch` and `GET /api/tryoff/jobs/{id}` endpoints
- **@tanstack/react-query**: Already installed — used for polling (not SWR as originally noted)
- **shadcn/ui components**: Existing `Card`, `Badge`, `Button`, `Skeleton`, `Alert` — need to build Dropzone inline (no react-dropzone installed)

### Technical Approach

**Route Structure** (Next.js 16 App Router):
```
app/
  (dashboard)/
    tryoff/
      new/
        page.tsx          # Upload + selector (combined flow)
      status/
        page.tsx          # Job status display
```

**Component Map**:
- `components/tryoff/image-dropzone.tsx` — Drag-and-drop zone with preview, validation
- `components/tryoff/garment-chips.tsx` — Multi-select toggle chips
- `components/tryoff/job-card.tsx` — Individual job status card
- `components/tryoff/job-list.tsx` — Grid of job cards

**API Integration**:
- `lib/api/tryoff.ts` — API functions for batch submit and job status
- `hooks/use-tryoff-jobs.ts` — React Query hook with polling (2s → 10s exponential backoff, stops when all jobs terminal)

**State Flow**:
1. User drops/selects image → preview shown via `URL.createObjectURL`
2. User selects garment types → chips highlight
3. User clicks "Start Extraction" → image uploaded to backend, then batch job submitted
4. Navigate to `/tryoff/status?job_ids=id1,id2`
5. Status page polls each job until all terminal

**Polling Strategy**:
- Use `@tanstack/react-query` `useQuery` with `refetchInterval`
- Interval function: `2000 * Math.min(2 ^ attemptCount, 5)` → caps at ~10s
- Stop polling when all jobs have status `complete` or `failed`

### Acceptance Criteria

- [ ] Mayorista can upload image, select 2 garment types, submit, and see 2 job cards with live status
- [ ] Job cards update without page refresh (React Query polling)
- [ ] Completed job card shows extracted garment thumbnail
- [ ] Failed job card shows error message
- [ ] Non-image files rejected with "Please upload a JPEG or PNG image"
- [ ] Files > 10 MB rejected with "Image must be under 10 MB"
- [ ] "Start Extraction" disabled when no garment type selected
- [ ] Polling stops when all jobs reach terminal state
