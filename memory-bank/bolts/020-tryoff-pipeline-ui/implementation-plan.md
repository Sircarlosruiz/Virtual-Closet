---
stage: plan
bolt: 020-tryoff-pipeline-ui
created: 2026-06-01T14:35:00Z
---

## Implementation Plan: 020-tryoff-pipeline-ui

### Objective
Add extracted garment filtering to the existing media library and implement the "Use in VTON" one-click navigation action that closes the TryOff → VTON loop.

### Deliverables
1. **"Extracted Garments" filter chip** in the media library filter bar — queries `GET /api/media?type=extracted_garment`
2. **Garment type badge overlay** on gallery items showing Upper / Lower / Dress
3. **Detail panel enhancements** for extracted garments — full-size image, source image reference, extraction date
4. **"Use in VTON ↗" button** in two locations:
   - Media gallery item detail panel (story 004)
   - Completed job card on the extraction status page (story 005 — already partially covered by bolt 019, needs verification)
5. **Empty state** for when no extracted garments exist — CTA "Extract your first garment"
6. **VTON submission page query param support** — `/vton/new?garment_id=<media_id>` pre-fills the garment field (coordinate with intent 001 frontend)

### Dependencies
- **002-tryoff-job-service / 005-media-library-save**: Extracted garments must already be saved as MediaItems with `type: extracted_garment`
- **Existing media library UI components**: Reuse gallery grid, filter bar, and detail drawer/sheet
- **Existing VTON submission page** (`/vton/new`): Must accept `?garment_id` query param — if not yet implemented, this bolt will add it
- **shadcn/ui**: Badge component for garment type labels

### Technical Approach
1. **Filter integration**:
   - Locate existing media library page (likely `frontend/app/(dashboard)/media/page.tsx` or similar)
   - Add "Extracted Garments" chip to the filter bar alongside existing filter options
   - When active, append `type=extracted_garment` to the media API query

2. **Gallery item badge**:
   - Media items for extracted garments carry metadata (garment_type, extraction_date)
   - Overlay a shadcn Badge on the thumbnail grid item showing garment type
   - Reuse existing badge variants (e.g., `variant="secondary"` or custom color)

3. **Detail panel**:
   - Reuse existing media item detail drawer/sheet component
   - Add fields: full-size image, source image thumbnail + link, extraction date, garment type
   - Add "Use in VTON ↗" button that calls `router.push("/vton/new?garment_id=" + mediaId)`

4. **"Use in VTON" on status page**:
   - Bolt 019 created the status page with job cards
   - Verify completed job cards have the "Use in VTON ↗" button
   - If missing, add it to the completed job card component

5. **VTON submission page**:
   - Locate `/vton/new` page (likely `frontend/app/(dashboard)/vton/new/page.tsx`)
   - Add `useSearchParams()` or `useRouter()` query param reading for `garment_id`
   - On mount, if `garment_id` present, fetch garment details via existing media API and pre-select
   - Handle graceful degradation if garment not found

6. **Empty state**:
   - When filter is active and API returns 0 items, show empty state with illustration and CTA button linking to `/tryoff/new`

### Acceptance Criteria
- [ ] "Extracted Garments" filter in media library shows only extracted garment items
- [ ] Each item shows garment type badge and extraction date
- [ ] Clicking "Use in VTON" on any extracted garment navigates to `/vton/new?garment_id=<id>`
- [ ] Empty state shown when no extracted garments exist
- [ ] VTON submission page pre-fills garment when `?garment_id` is present
- [ ] "Use in VTON" button visible on completed job cards in status page
