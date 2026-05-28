---
stage: plan
bolt: 009-catalog-management-ui
created: 2026-05-28T19:30:00Z
---

## Implementation Plan: 003-catalog-management-ui

### Objective

Build the mayorista's core catalog management interface: a dashboard to browse and create catalogs, a detail page to manage catalog items (add, remove, reorder), and publish/unpublish/delete flows with confirmation dialogs.

### Deliverables

1 - **Catalog List Page** (`/catalogs`)
   - Grid/list view of all mayorista's catalogs
   - Each catalog card shows: name, status badge (Draft/Published), item count, last updated
   - "Create Catalog" button opens modal form
   - Empty state with CTA when no catalogs exist
   - Click catalog → navigate to detail page

2 - **Catalog Detail Page** (`/catalogs/{id}`)
   - Header with catalog name (editable), status badge, action buttons
   - Item grid showing VTON images with metadata (name, price, cloth type, SKU)
   - "Add Item" button opens picker from completed VTON jobs
   - Remove item with confirmation modal
   - Reorder via drag-and-drop or up/down arrows
   - Publish/Unpublish/Delete actions in header

3 - **Shared Components**
   - `CatalogCard` - Reusable card for catalog list
   - `CatalogItemCard` - Item card with image and metadata
   - `CreateCatalogModal` - Modal form for creating catalogs
   - `AddItemPicker` - Modal with VTON job selector + metadata form
   - `ConfirmDialog` - Reusable confirmation modal
   - `StatusBadge` - Draft (grey) / Published (green) badge

4 - **API Integration Layer**
   - React Query hooks for all catalog endpoints
   - Optimistic updates for reorder and status changes
   - Error handling with toast notifications

### Dependencies

- **006-catalog-service APIs** (complete): Catalog CRUD + item management
- **007-catalog-service APIs** (complete): Publish/unpublish, delete, list, rename
- **VTON job API** (intent 001, complete): `GET /api/vton/jobs?status=completed` for item picker
- **React Query**: Server state management (assumed available in project)
- **Existing component library**: Design system components (buttons, modals, cards, forms)
- **Drag-and-drop library**: For item reorder (e.g., `@dnd-kit/core` or `react-beautiful-dnd`)

### Technical Approach

**Routing**: Next.js App Router pages under `app/catalogs/`
- `app/catalogs/page.tsx` - Catalog list
- `app/catalogs/[id]/page.tsx` - Catalog detail

**State Management**: React Query for all server state
- `useCatalogs()` - List catalogs with pagination
- `useCatalog(id)` - Single catalog with items
- `useCreateCatalog()` - Mutation with optimistic update
- `useAddCatalogItem()` - Mutation
- `useRemoveCatalogItem()` - Mutation with optimistic update
- `useReorderCatalogItems()` - Mutation with optimistic update
- `useUpdateCatalog()` - Mutation for rename/publish/unpublish
- `useDeleteCatalog()` - Mutation with redirect on success
- `useCompletedVtonJobs()` - For item picker

**Image Handling**: Pre-signed URLs fetched fresh on each page load (no client-side caching across navigations). Images rendered via `<img src={preSignedUrl}>`.

**Reorder UX**: Drag-and-drop with fallback up/down arrow buttons. Optimistic UI update on drop, PATCH request in background, revert on failure with error toast.

**Publish Guard**: Publish button disabled when `item_count === 0` with tooltip "Add at least one item before publishing".

**Error Handling**: All mutations show error toasts on failure. API errors on page load show error state with retry button.

### Acceptance Criteria

**Story 001 - Catalog List Page**:
- [ ] Catalogs displayed as cards with name, status badge, item count, updated date
- [ ] Empty state with "Create your first catalog" CTA when no catalogs
- [ ] "Create Catalog" modal accepts name and creates draft catalog
- [ ] New catalog appears in list without full page reload
- [ ] Clicking catalog navigates to detail page

**Story 002 - Catalog Detail Page**:
- [ ] Catalog name, status, and item grid displayed on load
- [ ] "Add Item" picker shows completed VTON jobs with metadata form
- [ ] Remove item with confirmation → item disappears, count updates
- [ ] Reorder via drag-and-drop or arrows → saved via PATCH, reflected immediately
- [ ] Catalog name editable inline or via modal → updates via PATCH

**Story 003 - Publish Flow**:
- [ ] Publish button shows confirmation dialog
- [ ] Confirmed publish → status badge changes to "Published" + success toast
- [ ] Publish button disabled with tooltip when catalog has 0 items
- [ ] Unpublish shows confirmation warning buyers will lose access
- [ ] Confirmed unpublish → status badge changes to "Draft"
- [ ] Delete Catalog with confirmation → redirects to catalog list

### File Structure

```
frontend/
├── app/
│   └── catalogs/
│       ├── page.tsx                    # Catalog list page
│       ├── layout.tsx                  # Catalog section layout
│       └── [id]/
│           └── page.tsx                # Catalog detail page
├── components/
│   └── catalogs/
│       ├── CatalogCard.tsx             # Catalog card for list view
│       ├── CatalogItemCard.tsx         # Item card with image + metadata
│       ├── CreateCatalogModal.tsx      # Create catalog form modal
│       ├── AddItemPicker.tsx           # VTON job picker + metadata form
│       ├── ConfirmDialog.tsx           # Reusable confirmation modal
│       ├── StatusBadge.tsx             # Draft/Published badge
│       └── ReorderControls.tsx         # Drag-and-drop + arrow buttons
├── hooks/
│   └── useCatalogs.ts                # React Query hooks for catalog APIs
└── lib/
    └── api/
        └── catalogs.ts               # API client functions for catalog endpoints
```
