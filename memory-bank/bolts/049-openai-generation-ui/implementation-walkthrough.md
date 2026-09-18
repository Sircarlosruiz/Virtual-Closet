---
stage: implement
bolt: 049-openai-generation-ui
created: 2026-09-18T16:55:00Z
---

## Implementation Walkthrough: 004-openai-generation-ui

### Summary

Staff now have a Virtual Closet surface to submit the four generation modes, poll job status, recompose SKU versions, and select or discard publication candidates with per-destination sync. BFashion reaches the same flow through a deep link that preserves product and wholesaler context. Non-staff users see no generation navigation or form.

### Structure Overview

Cookie-authenticated Next.js pages under a staff route group consume existing generation, template, composition, and publication APIs. A thin backend lookup resolves explicit product links from BFashion identifiers without inferring ownership from SKU. Role is exposed on the session profile so layouts can hide staff chrome before any generation request is made.

### Completed Work

- [x] `backend/api/schemas/auth.py` - Adds role on the session profile response
- [x] `backend/api/routers/auth.py` - Returns the authenticated actor role
- [x] `backend/api/schemas/product_link.py` - Lookup response for explicit product links
- [x] `backend/api/routers/product_links.py` - Staff cookie lookup that fails closed
- [x] `backend/main.py` - Registers the product-link router
- [x] `backend/tests/test_product_link_lookup.py` - Role and fail-closed lookup cases
- [x] `frontend/lib/api.ts` - Structured API errors with status and domain code
- [x] `frontend/lib/api/auth.ts` - Profile role helper for staff gating
- [x] `frontend/lib/auth/get-server-me.ts` - Shared server session loader
- [x] `frontend/lib/api/image-generation.ts` - Job create, status, and retry client
- [x] `frontend/lib/api/templates.ts` - Selectable templates and snapshot client
- [x] `frontend/lib/api/composition.ts` - SKU compose and version list client
- [x] `frontend/lib/api/publications.ts` - Candidate, decision, and retry client
- [x] `frontend/lib/api/product-links.ts` - Product-link lookup client
- [x] `frontend/lib/staff-generation/validate-generation-form.ts` - Mode validation and deep-link href helper
- [x] `frontend/components/staff-generation/StaffGate.tsx` - Client-side staff render gate
- [x] `frontend/components/staff-generation/StaffUnauthorized.tsx` - Generic unauthorized copy with no private data
- [x] `frontend/components/staff-generation/ProductContextBanner.tsx` - BFashion product context and link resolution
- [x] `frontend/components/staff-generation/GenerationModeForm.tsx` - Four-mode form, provider choice, and client validation
- [x] `frontend/components/staff-generation/JobReviewPanel.tsx` - Status polling, preview, snapshot, and retry
- [x] `frontend/components/staff-generation/SkuRecomposeForm.tsx` - New SKU version without replacing the original
- [x] `frontend/components/staff-generation/PublicationGallery.tsx` - Select, discard, and per-destination sync
- [x] `frontend/app/(staff)/staff/generation/layout.tsx` - Server staff gate and dashboard shell
- [x] `frontend/app/(staff)/staff/generation/page.tsx` - Staff form and BFashion entry contract
- [x] `frontend/app/(staff)/staff/generation/[jobId]/page.tsx` - Review, recompose, and publication page
- [x] `frontend/app/(dashboard)/layout.tsx` - Passes role into the shared shell
- [x] `frontend/app/dashboard/layout.tsx` - Passes role into the shared shell
- [x] `frontend/components/dashboard/DashboardShell.tsx` - Forwards role to navigation
- [x] `frontend/components/dashboard/AppSidebar.tsx` - Staff-only Generación IA link
- [x] `frontend/components/dashboard/dashboard-nav.ts` - Titles for staff generation routes

### Key Decisions

- **Deep link instead of a BFashion Vite screen**: the ecommerce app stays in its own repo; Virtual Closet preserves query context and documents the entry URL.
- **Lookup by explicit link, never SKU**: publication still requires a persisted product link resolved fail-closed for the staff tenant.
- **Client validation before POST**: invalid forms never create a job; the API remains the source of truth.
- **Staff chrome is opt-in**: mayorista navigation is unchanged; generation appears only for staff roles.

### Deviations from Plan

- Frontend component and Playwright tests were deferred to Stage 3, as required by the simple-construction bolt type. Backend lookup tests were added here because they cover the new cookie API.
- Snapshot capture on job create is still a backend gap; the UI prefills from selectable templates and shows a snapshot only when one exists.

### Dependencies Added

None.

### Developer Notes

- Apply existing Alembic revisions through publication (`f6a7b8c9d0e1`) before using these screens.
- BFashion should open `/staff/generation?source=bfashion&external_product_id=...&external_wholesaler_id=...&sku=...` with a staff cookie session.
- Overlay-fit errors surface from the structured API code `OVERLAY_DOES_NOT_FIT`.
