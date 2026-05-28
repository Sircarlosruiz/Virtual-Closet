---
stage: plan
bolt: 004-vton-pipeline-ui
created: 2026-05-27T00:00:00Z
---

## Implementation Plan: 004-vton-pipeline-ui

### Objective

Build the three-step VTON generation form as a Next.js 14 App Router page at `/dashboard/generate` with reusable shadcn/ui components for garment upload, model selection, and job submission.

### Deliverables

1. **Page**: `app/(dashboard)/generate/page.tsx` — Main generation flow page with form state management
2. **Component**: `components/vton/GarmentUploader.tsx` — Drag-and-drop garment upload with preview, validation, and upload to `POST /api/media/garments`
3. **Component**: `components/vton/ModelSelector.tsx` — Tabbed panel with "My Models" (own uploads) and "Model Library" (curated) tabs, grid of thumbnails, selection state
4. **Component**: `components/vton/ClothTypeSelector.tsx` — Radio/segmented control for cloth type (`upper_body`, `lower_body`, `dress`)
5. **Form State**: Manage form state across all three steps with validation and disabled states for Generate button

### Dependencies

- **001-media-service**: Upload endpoints (`POST /api/media/garments`, `POST /api/media/models`) and model library endpoints (`GET /api/media/models/mine`, `GET /api/media/models/curated`) must exist
- **002-vton-job-service**: Job submission endpoint (`POST /api/vton/generate`) must exist
- **shadcn/ui**: `Tabs`, `RadioGroup`, `Button`, `Input`, `Badge`, `Skeleton`, `Dialog` components
- **Next.js 14 App Router**: Route group `(dashboard)` must exist

### Technical Approach

1. **Form State**: Use React `useState` at the page level to track `garmentId`, `modelId`, `clothType`, and submission state. Pass callbacks to child components.
2. **GarmentUploader**: 
   - Client component with drag-and-drop zone using native HTML5 DnD API
   - Client-side validation: JPG/PNG only, ≤10MB
   - Preview via `URL.createObjectURL()`
   - Upload via `fetch` to `POST /api/media/garments` with FormData
   - Loading indicator during upload, success state with thumbnail
3. **ModelSelector**:
   - Client component using shadcn `Tabs` for "My Models" / "Model Library"
   - Fetch models on tab mount via `GET /api/media/models/mine` and `GET /api/media/models/curated`
   - Grid layout: 2 columns mobile, 3-4 columns desktop
   - Upload prompt when "My Models" is empty
   - Selection state with ring-2 + checkmark overlay
4. **ClothTypeSelector**:
   - Client component using shadcn `RadioGroup` or segmented tabs
   - Values must match API enum: `upper_body`, `lower_body`, `dress`
5. **Generate Button**:
   - Disabled when any of: missing garment, missing model, missing cloth type, or submitting
   - On click: `POST /api/vton/generate` with `{garment_id, model_id, cloth_type}`
   - On success: redirect to `/dashboard/jobs/{job_id}` via `router.push`
   - On error: toast notification, form remains for retry
6. **Mobile-First**: All components must work at 375px viewport
7. **Accessibility**: WCAG AA — all inputs keyboard accessible, proper labels, focus management

### Acceptance Criteria

- [ ] Garment upload works with drag-and-drop and file picker on mobile
- [ ] Model selector shows own models and curated library in tabs
- [ ] Cloth type required before Generate button is enabled
- [ ] Successful submission redirects to `/dashboard/jobs/{job_id}`
- [ ] All error states handled (validation, API errors)
- [ ] WCAG AA: all inputs keyboard accessible
- [ ] Layout works at 375px (mobile) and 1280px (desktop)
