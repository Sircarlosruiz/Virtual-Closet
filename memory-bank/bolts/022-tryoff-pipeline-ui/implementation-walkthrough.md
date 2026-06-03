---
stage: implement
bolt: 022-tryoff-pipeline-ui
created: 2026-06-03T00:00:00Z
---

## Implementation Walkthrough: 022-tryoff-pipeline-ui

### Summary

Added an extraction shortcut card to the mayorista dashboard (`DashboardContent.tsx`) that links to `/extraction/new`. The card uses the existing dashboard styling patterns with a `Shirt` icon, hover effects, and Spanish labels consistent with the rest of the UI.

### Structure Overview

Single file change: added a `<Link>` wrapped card component between the stats strip and the garment section in `DashboardContent.tsx`.

### Completed Work

- [x] `frontend/components/dashboard/DashboardContent.tsx` — Added extraction shortcut card with `Shirt` icon, "Extraer prendas" label, and navigation to `/extraction/new`

### Key Decisions

- **Placement**: Between stats strip and "Mis prendas" section — first actionable item after the overview
- **Styling**: Matches existing dashboard card patterns (`rounded-xl border bg-card p-4`) with hover shadow and color transitions
- **Icon**: `Shirt` from lucide-react — semantically appropriate and already used elsewhere in the project

### Deviations from Plan

- None

### Dependencies Added

- None

### Developer Notes

- The 2 pre-existing ESLint errors (`@typescript-eslint/no-explicit-any` on lines 15-16) are unrelated to this change
