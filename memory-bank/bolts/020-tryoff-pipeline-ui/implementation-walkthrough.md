---
stage: implement
bolt: 020-tryoff-pipeline-ui
created: 2026-06-01T14:45:00Z
---

## Implementation Walkthrough: 020-tryoff-pipeline-ui

### Summary

Added extracted garment filtering to the media library and implemented the "Use in VTON" one-click navigation action. This closes the TryOff → VTON loop by allowing mayoristas to browse their extracted garments and apply them to new VTON jobs without re-uploading.

### Structure Overview

Backend changes add new API endpoints for listing and retrieving extracted garments from the `media_items` table. Frontend changes add a dedicated extracted garments page, a detail panel via Sheet component, and query param support on the VTON submission page. The TryOff job card now includes a "Use in VTON" button for completed jobs.

### Completed Work

- [x] `backend/api/schemas/media.py` - Added ExtractedGarmentResponse and PaginatedExtractedGarments schemas
- [x] `backend/api/routers/media.py` - Added GET /api/media/extracted-garments (paginated list) and GET /api/media/extracted-garments/{id} (single item)
- [x] `backend/services/media_library_service.py` - Added list_extracted_garments, get_garment_by_id, get_presigned_url methods
- [x] `backend/models/tryoff_job.py` - Added output_media_id column to link jobs to extracted garments
- [x] `backend/api/schemas/tryoff.py` - Added output_media_id to TryoffJobStatusResponse and TryoffJobHistoryItem
- [x] `backend/services/tryoff_job_service.py` - Added output_media_id to job status and list responses
- [x] `backend/tasks/tryoff_task.py` - Store output_media_id when saving extracted garment to media library
- [x] `backend/alembic/versions/a3b4c5d6e7f8_add_output_media_id_to_tryoff_jobs.py` - Migration for new column
- [x] `frontend/lib/api/extracted-garments.ts` - API client for extracted garments endpoints
- [x] `frontend/lib/api/tryoff.ts` - Added output_media_id to TryoffJob type
- [x] `frontend/components/tryoff/extracted-garment-card.tsx` - Card component with garment type badge and "Use in VTON" button
- [x] `frontend/components/tryoff/extracted-garments-grid.tsx` - Grid with pagination, empty state, and detail Sheet panel
- [x] `frontend/components/tryoff/job-card.tsx` - Added "Use in VTON" button for completed jobs
- [x] `frontend/app/(dashboard)/generate/page.tsx` - Added ?garment_id query param support with preloaded garment display
- [x] `frontend/app/(dashboard)/media/extracted/page.tsx` - Dedicated extracted garments page
- [x] `frontend/components/dashboard/DashboardContent.tsx` - Added navigation button to extracted garments page

### Key Decisions

- **Dedicated page vs filter**: Created `/dashboard/media/extracted` as a separate page rather than modifying the existing dashboard prendas grid. This keeps the dashboard simple and provides a focused experience for extracted garments.
- **output_media_id on TryoffJob**: Added this column to link completed jobs directly to their extracted garment MediaItem, enabling the "Use in VTON" button on job cards without needing a separate lookup.
- **Query param handoff**: Used `?garment_id` query param for VTON handoff — the generate page reads it on mount, fetches the garment details, and displays it as pre-selected.

### Deviations from Plan

- None — all planned deliverables implemented as specified.

### Dependencies Added

- None — all changes use existing dependencies (shadcn/ui components, lucide-react, next/navigation).

### Developer Notes

- The extracted garments API returns presigned URLs that expire after 15 minutes — this is consistent with other media endpoints.
- The `?garment_id` param on the generate page uses a ref guard (`hasLoadedRef`) to prevent re-fetching on re-renders.
- Garment type badges use different shadcn variants (default/secondary/outline) to visually distinguish upper/lower/dress types.
