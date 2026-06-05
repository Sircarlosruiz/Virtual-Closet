---
stage: implement
bolt: 027-batch-vton-generation-ui
created: 2026-06-04T00:00:00Z
---

## Implementation Walkthrough: batch-vton-generation-ui (Bolt 027)

### Summary

Added retry interaction to failed batch items on the progress page with optimistic updates and React Query cache invalidation. Implemented the batch history listing page with pagination, status badges, and empty state CTA.

### Structure Overview

Updated existing BatchItemRow and BatchProgressPage components, added new BatchHistoryPage at `/batches` route. Retry uses React Query `useMutation` with `onMutate` for optimistic updates, `onError` for rollback, and `onSettled` for cache invalidation.

### Completed Work

- [x] `components/batch/BatchItemRow.tsx` - Updated to support `isRetrying` and `retryError` props, shows loading spinner during retry, disables button while in flight
- [x] `app/(dashboard)/batches/[batchId]/page.tsx` - Added `useMutation` for retry with optimistic update (status → pending), rollback on error, cache invalidation on settled
- [x] `app/(dashboard)/batches/page.tsx` - BatchHistoryPage with paginated list, status badges (complete/partial/failed/in-progress), empty state with CTA, "New Batch" button, clickable rows navigating to progress page

### Key Decisions

- **React Query `useMutation` for retry**: Used `onMutate` for optimistic update, `onError` for rollback with context snapshot, `onSettled` for cache invalidation. This is the standard React Query pattern for optimistic updates.
- **Per-item retry state**: Used `retryingItemId` state to track which item is being retried. Only one retry at a time per page.
- **No pagination state yet**: History page loads page 1 with 20 items. Pagination controls are shown but not wired to state yet (can be added later).
- **Clickable rows**: Batch rows in history page are clickable Cards that navigate to the progress page.

### Deviations from Plan

- **No `isRetrying` per-item state array**: Used single `retryingItemId` string instead of a map. Simpler since only one retry happens at a time.
- **Pagination not fully wired**: Pagination controls are rendered but only page 1 is loaded. Full pagination requires state management for page number.

### Dependencies Added

None. All dependencies (React Query, lucide-react, shadcn/ui components) were already in the project.

### Developer Notes

- The optimistic update sets item status to `pending` and clears `error_message`. On error, the entire batch query data is rolled back to the snapshot taken in `onMutate`.
- After retry settles, `invalidateQueries` triggers a refetch which will pick up the new status from the server.
- The existing 3s polling continues to run, so even if cache invalidation fails, the status will eventually update.
