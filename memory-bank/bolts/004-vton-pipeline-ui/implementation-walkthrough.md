---
stage: implement
bolt: 004-vton-pipeline-ui
created: 2026-05-27T00:10:00Z
---

## Implementation Walkthrough: 004-vton-pipeline-ui

### Summary

Built the three-step VTON generation form at `/dashboard/generate` with four reusable components: GarmentUploader for drag-and-drop photo upload, ModelSelector for tabbed model selection (own + curated), ClothTypeSelector for cloth type radio selection, and the main page orchestrating form state and job submission.

### Structure Overview

All components are client components under `components/vton/` with the page at `app/(dashboard)/generate/page.tsx`. Form state is managed at the page level with React `useState`, passed as callbacks to child components.

### Completed Work

- [x] `components/vton/GarmentUploader.tsx` — Drag-and-drop upload zone with client-side validation (JPG/PNG, ≤10MB), local preview via `URL.createObjectURL()`, upload to `POST /api/media/garments`, success/error states, clear functionality
- [x] `components/vton/ModelSelector.tsx` — Tabbed panel with "Mis Modelos" and "Biblioteca" tabs, thumbnail grid (2-col mobile, 3-4 col desktop), selection state with ring indicator, inline uploader for new models, fetches from `/api/media/models/mine` and `/api/media/models/curated`
- [x] `components/vton/ClothTypeSelector.tsx` — Radio group with three options (Parte Superior, Parte Inferior, Vestido), values match API enum exactly, styled labels with selected state
- [x] `app/(dashboard)/generate/page.tsx` — Main page with three Card sections (upload → select → submit), form state management, Generate button with disabled states and loading spinner, redirect to `/dashboard/jobs/{job_id}` on success
- [x] `components/ui/tabs.tsx` — shadcn/ui Tabs component (newly installed)
- [x] `components/ui/radio-group.tsx` — shadcn/ui RadioGroup component (newly installed)
- [x] `components/ui/skeleton.tsx` — shadcn/ui Skeleton component (newly installed)

### Key Decisions

- **Form State at Page Level**: Single source of truth for `garmentId`, `modelId`, `clothType` — avoids prop drilling and keeps submission logic centralized
- **Native HTML5 DnD**: No external library needed, lighter bundle
- **`<img>` over `next/image`**: Presigned URLs have expiry timestamps — Next.js image optimization would cache beyond expiry
- **Spanish UI Labels**: All user-facing text in Spanish (mayorista audience)
- **Toast Notifications**: Using existing `sonner` integration for success/error feedback

### Deviations from Plan

None — implementation follows the plan exactly.

### Dependencies Added

- [x] `tabs` — shadcn/ui component for ModelSelector tabbed interface
- [x] `radio-group` — shadcn/ui component for ClothTypeSelector
- [x] `skeleton` — shadcn/ui component for loading states

### Developer Notes

- The `GarmentUploader` receives `uploadedId` prop to show success state — when set, it shows the preview with a "Seleccionada" badge and clear button
- `ModelSelector` fetches both tabs on mount in parallel for faster initial load
- Cloth type values must match backend enum exactly: `upper_body`, `lower_body`, `dress`
- The Generate button shows contextual hints when disabled (what's missing)
