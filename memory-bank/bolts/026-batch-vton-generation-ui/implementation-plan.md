---
stage: plan
bolt: 026-batch-vton-generation-ui
created: 2026-06-04T00:00:00Z
---

## Implementation Plan: batch-vton-generation-ui (Bolt 026)

### Objective

Implement the two core UI pages for batch VTON generation: the batch creation wizard (garment + model pairing selection, submit) and the real-time batch progress monitoring page with per-item status polling.

### Deliverables

1. **`app/(dashboard)/batches/new/page.tsx`** — BatchCreatePage: Garment selection grid from media library, model pairing rows with cloth type picker, batch name input, submit button with live count
2. **`app/(dashboard)/batches/[batchId]/page.tsx`** — BatchProgressPage: Batch name, progress bar, completed/failed/in-progress counters, per-item list with status badges, 3s polling that stops on terminal state
3. **`components/batch/BatchItemRow.tsx`** — Reusable row component: garment thumbnail, model thumbnail, cloth type label, status badge (Pending/Processing/Done/Failed), error message display
4. **`lib/api/batches.ts`** — API client: `createBatch()`, `getBatch()`, TypeScript types for request/response
5. **`lib/api/media.ts`** — API client: `listGarments()`, `listModels()` (reuse or extend existing media API client)

### Dependencies

- **025-batch-job-service** (complete): `POST /api/batches`, `GET /api/batches/{id}` endpoints available
- **Existing media library API**: `GET /api/media` for garment and model photo listing
- **Existing component library**: Reuse thumbnail, badge, progress bar, and form components from `003-vton-pipeline-ui`
- **React Query**: For data fetching, caching, and polling (`refetchInterval`)

### Technical Approach

1. **BatchCreatePage**:
   - Fetch garments from media library API on mount
   - Grid selection with checkbox (max 100, disabled tooltip on 101st)
   - Each selected garment renders a `PairingRow` with model dropdown and cloth type selector
   - Form state managed with `useState` or `useReducer` (pairings array)
   - Submit: `POST /api/batches` → on success, `router.push(/batches/${batchId})`
   - Error handling: toast on API failure, form stays open

2. **BatchProgressPage**:
   - Fetch batch on mount via `GET /api/batches/{batchId}`
   - Poll every 3s using React Query `refetchInterval: (data) => data?.status === 'in-progress' ? 3000 : false`
   - Progress bar: `completed_count / total_items`
   - Per-item list: `BatchItemRow` for each item, status badge with color coding
   - Terminal state banner: green (complete), orange (partial), red (failed)
   - Network error handling: "Connection lost" indicator with auto-resume

3. **BatchItemRow**:
   - Props: `item` (BatchItemResponse), `onRetry?` (optional, for bolt 027)
   - Status badge: gray (pending), blue spinner (processing), green check (done), red X (failed)
   - Error message: truncated to 120 chars with "Show more" expand
   - Click on completed item: opens result in media library (future)

### Acceptance Criteria

- [ ] Mayorista can select 1–100 garments and configure pairings with model + cloth type
- [ ] Submit button shows pairing count and is disabled when 0 pairings
- [ ] On submit success, redirect to BatchProgressPage with correct batchId
- [ ] Progress page shows batch name, progress bar, and counters
- [ ] Status updates automatically every 3s while batch is in-progress
- [ ] Polling stops when batch reaches terminal state (complete/partial/failed)
- [ ] Each item row shows garment thumbnail, model thumbnail, cloth type, and status badge
- [ ] Failed items show error message (truncated with expand)
- [ ] 100-item batch renders without performance issues (virtualized if needed)
