---
stage: implement
bolt: 009-catalog-management-ui
created: 2026-05-28T20:00:00Z
---

# Implementation Walkthrough: 009-catalog-management-ui

## Summary

Implemented the complete catalog management UI for mayoristas, including:
- Catalog list page with create modal and empty state
- Catalog detail page with item grid, add/remove/reorder, and publish/unpublish/delete flows
- Backend `GET /api/catalogos/{id}` endpoint for detail page
- React Query hooks for all catalog operations
- Shared components (StatusBadge, CatalogCard, CatalogItemCard, CreateCatalogModal, AddItemPicker, ConfirmDialog)

## Files Created/Modified

### Backend
- `backend/api/routers/catalogo.py` — Added `GET /{catalog_id}` endpoint
- `backend/api/schemas/catalogo.py` — Already had `CatalogoDetailResponse` (previous session)
- `backend/services/catalogo_service.py` — Already had `get_catalog_with_items` (previous session)

### Frontend
- `frontend/lib/api/catalogos.ts` — API client (created previous session)
- `frontend/lib/api/vton.ts` — VTON jobs API client (new)
- `frontend/hooks/useCatalogos.ts` — React Query hooks (new)
- `frontend/components/catalogos/StatusBadge.tsx` — Status badge component (new)
- `frontend/components/catalogos/CatalogCard.tsx` — Catalog card for list view (new)
- `frontend/components/catalogos/CatalogItemCard.tsx` — Item card with reorder/delete (new)
- `frontend/components/catalogos/CreateCatalogModal.tsx` — Create catalog modal (new)
- `frontend/components/catalogos/AddItemPicker.tsx` — VTON job picker + metadata form (new)
- `frontend/components/catalogos/ConfirmDialog.tsx` — Reusable confirmation dialog (new)
- `frontend/app/dashboard/catalogos/page.tsx` — Catalog list page (new)
- `frontend/app/dashboard/catalogos/[id]/page.tsx` — Catalog detail page (new)

## Key Implementation Details

### Backend
- `GET /api/catalogos/{catalog_id}` returns catalog with items and pre-signed image URLs
- Uses existing `get_catalog_with_items` service method
- Validates ownership via `get_current_mayorista` dependency

### Frontend Hooks
- `useCatalogosList(page, pageSize)` — Paginated list query
- `useCatalogo(id)` — Single catalog detail query
- `useCreateCatalogo()` — Create mutation with invalidation
- `useUpdateCatalogo()` — Update mutation (name/status)
- `useDeleteCatalogo()` — Delete mutation with invalidation
- `useAddCatalogoItem()` — Add item mutation
- `useRemoveCatalogoItem()` — Remove item mutation
- `useReorderCatalogoItems()` — Reorder mutation

### Reorder Logic
- Uses up/down arrow buttons (no drag-and-drop dependency)
- Swaps adjacent items in local state, then submits full reorder via PATCH
- Backend validates bijection (all items must be included)

### Publish Guard
- Publish button disabled when `item_count === 0`
- Confirmation dialogs for publish, unpublish, and delete

### Form Handling
- Uses `react-hook-form` with `zodResolver` (no Form/FormField components available)
- Follows existing pattern from `login/page.tsx`

## TypeScript Verification
- `npx tsc --noEmit` passes with no errors

## Next Steps
- Manual testing with running backend
- E2E tests (Playwright)
- Implementation walkthrough review
