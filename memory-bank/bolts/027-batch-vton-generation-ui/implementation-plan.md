---
stage: plan
bolt: 027-batch-vton-generation-ui
created: 2026-06-04T00:00:00Z
---

## Implementation Plan: batch-vton-generation-ui (Bolt 027)

### Objective

Add retry interaction to failed batch items on the progress page and implement the batch history listing page with pagination and empty state.

### Deliverables

1. **`components/batch/BatchItemRow.tsx`** (updated) — Add retry button with loading state, optimistic update, and error handling
2. **`app/(dashboard)/batches/[batchId]/page.tsx`** (updated) — Wire up retry handler with optimistic update and React Query cache invalidation
3. **`app/(dashboard)/batches/page.tsx`** — BatchHistoryPage: paginated list of batches, status badges, empty state with CTA, "New Batch" shortcut

### Dependencies

- **026-batch-vton-generation-ui** (complete): BatchProgressPage and BatchItemRow exist
- **Backend API** (024 complete): `POST /api/batches/{id}/items/{item_id}/retry` endpoint available
- **Backend API** (023 complete): `GET /api/batches` list endpoint available
- **React Query**: For cache invalidation after retry

### Technical Approach

1. **Retry Button Integration**:
   - Extend `BatchItemRow` to accept `onRetry` callback and `isRetrying` prop
   - When clicked: optimistically set row status to `pending`, disable button, show spinner
   - Call `retryBatchItem(batchId, itemId)` from API client
   - On success: invalidate React Query cache for the batch (triggers refetch)
   - On error: revert status to `failed`, show inline error message
   - Use `useState` per item to track retry state (prevents double-clicks)

2. **BatchHistoryPage**:
   - Fetch batches via `listBatches(page, pageSize)` on mount
   - Render table/list with columns: name, created date, total items, completed/failed counts, status badge
   - Status badge colors: complete (green), partial (yellow), failed (red), in-progress (blue)
   - Empty state: "No batches yet" message with "Create your first batch" CTA linking to `/batches/new`
   - Pagination controls at bottom (Previous/Next buttons, page indicator)
   - "New Batch" button in page header

### Acceptance Criteria

- [ ] Retry button appears only on `failed` items
- [ ] Optimistic update on click (status → pending, button disabled with spinner)
- [ ] Revert to failed status on API error with inline error message
- [ ] Button disabled while request in flight (prevents double-clicks)
- [ ] History page loads and shows batches in reverse-chronological order
- [ ] Each row shows name, date, total items, completed/failed counts, status badge
- [ ] Empty state shows CTA to create first batch
- [ ] Pagination works for >20 batches
- [ ] Clicking a batch row navigates to BatchProgressPage
