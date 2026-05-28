---
stage: implement
bolt: 010-catalog-management-ui
created: 2026-05-28T22:00:00Z
---

## Implementation Walkthrough: 010-catalog-management-ui

### Summary

Implemented the customer management UI for mayoristas (register buyers, view customer list) and the buyer-facing portal (authenticate via invitation link, browse published catalogs). Added the missing `GET /api/customers` endpoint to the backend.

### Structure Overview

**Backend**: Added customer listing endpoint with pagination support.
**Frontend**: Two distinct areas — mayorista customer management under `/dashboard/customers` and buyer portal under `/portal/*` with separate layout and auth context.

### Completed Work

- [x] `backend/repositories/customer_repo.py` - Added `list_by_mayorista` method with pagination
- [x] `backend/services/customer_service.py` - Added `list_customers` method
- [x] `backend/api/schemas/customer.py` - Added `CustomerListResponse` schema
- [x] `backend/api/routers/customers.py` - Added `GET /` endpoint with pagination
- [x] `frontend/lib/api/customers.ts` - Customer API client (list + register)
- [x] `frontend/lib/api/portal.ts` - Portal API client (catalogs, detail, magic link)
- [x] `frontend/hooks/useCustomers.ts` - React Query hooks for customers
- [x] `frontend/hooks/usePortal.ts` - React Query hooks for portal
- [x] `frontend/components/customers/CustomerStatusBadge.tsx` - Invited/Active badge
- [x] `frontend/components/customers/RegisterCustomerModal.tsx` - Registration form modal
- [x] `frontend/components/portal/PortalCatalogCard.tsx` - Catalog card for buyer portal
- [x] `frontend/components/portal/PortalCatalogItemCard.tsx` - Read-only item card
- [x] `frontend/app/dashboard/customers/page.tsx` - Customer management page with table
- [x] `frontend/app/portal/layout.tsx` - Portal layout (no mayorista nav)
- [x] `frontend/app/portal/page.tsx` - Published catalog list for buyer
- [x] `frontend/app/portal/auth/page.tsx` - Invitation link handler
- [x] `frontend/app/portal/request-link/page.tsx` - Magic link request form
- [x] `frontend/app/portal/catalogs/[id]/page.tsx` - Catalog detail for buyer

### Key Decisions

- **Backend pagination**: Added `list_by_mayorista` to repo following same pattern as catalog listing
- **Portal layout**: Separate layout with minimal header, no sidebar navigation, distinct visual style
- **Buyer auth flow**: `/portal/auth?token=...` calls API → sets cookie → redirects to `/portal`
- **Error handling**: 401 on portal pages redirects to request-link page
- **Read-only portal**: No edit/delete controls, just catalog browsing

### Deviations from Plan

- None

### Dependencies Added

- None (all dependencies already available)

### Developer Notes

- Portal pages use `retry: false` on React Query to avoid infinite retry loops on 401
- Buyer session cookie is scoped to `/api/portal` path (backend handles this)
- Customer table uses simple table layout rather than cards for better density
