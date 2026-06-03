---
stage: plan
bolt: 022-tryoff-pipeline-ui
created: 2026-06-03T00:00:00Z
---

## Implementation Plan: 022-tryoff-pipeline-ui

### Objective

Add an extraction shortcut card to the mayorista dashboard that links to `/extraction/new`.

### Deliverables

1. **`components/dashboard/DashboardContent.tsx`** — Add extraction shortcut card between stats strip and garment section

### Dependencies

- Dashboard page exists (confirmed at `app/dashboard/page.tsx` → `DashboardContent`)
- `/extraction/new` route exists (bolt 019)

### Technical Approach

- Add a `<Link>` wrapping a styled card div in `DashboardContent.tsx`
- Use `Shirt` icon from lucide-react (already imported in extracted-garments-grid)
- Label: "Extraer prendas", description: "Extrae prendas de tus imágenes para usarlas en VTON"
- Follow existing card styling: `rounded-xl border bg-card p-4`, hover shadow, group hover color transitions
- Place between stats strip and "Mis prendas" section

### Acceptance Criteria

- [ ] Extraction shortcut card visible on dashboard
- [ ] Click navigates to `/extraction/new`
- [ ] Card follows existing dashboard styling patterns
- [ ] ESLint passes (no new errors)
