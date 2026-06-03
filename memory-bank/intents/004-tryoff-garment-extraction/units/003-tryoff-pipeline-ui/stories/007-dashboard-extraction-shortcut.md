---
id: 007-dashboard-extraction-shortcut
unit: 003-tryoff-pipeline-ui
intent: 004-tryoff-garment-extraction
status: complete
priority: should
created: 2026-06-03T00:00:00.000Z
assigned_bolt: null
implemented: true
---

# Story: 007-dashboard-extraction-shortcut

## User Story

**As a** mayorista
**I want** a shortcut on my dashboard to access the garment extraction page
**So that** I can quickly start extracting garments without navigating through menus

## Acceptance Criteria

- [ ] **Given** I am on the dashboard (`/dashboard`), **When** I look at the page, **Then** I see a card/tile labeled "Extraer prendas" (or similar) with a brief description
- [ ] **Given** the extraction shortcut card is visible, **When** I click it, **Then** I am navigated to `/extraction/new`
- [ ] **Given** I am on the dashboard, **When** I view the shortcut card, **Then** it includes an icon (e.g., `Shirt` or `Scissors` from lucide-react) consistent with the dashboard's existing card style
- [ ] **Given** the dashboard has multiple shortcut cards, **When** the extraction card is rendered, **Then** it follows the same layout/styling pattern as existing dashboard cards

## Technical Notes

- Place the shortcut in the existing dashboard page (`app/(dashboard)/dashboard/page.tsx` or equivalent)
- Use existing card component patterns from the dashboard
- Icon: `Shirt` from lucide-react (already used in extracted-garments-grid)
- Label: "Extraer prendas" (Spanish, consistent with existing UI language)
- Description: "Extrae prendas de tus imágenes para usarlas en VTON"
- No backend changes needed — pure frontend navigation

## Dependencies

### Requires
- Dashboard page exists (from intent 001 or 002)
- `/extraction/new` route exists (bolt 019)

### Enables
- Faster access to extraction flow for mayoristas

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Dashboard already has many cards | Extraction card fits into existing grid layout |
| User has no extraction history | Card still visible (it's a shortcut, not conditional) |

## Out of Scope

- Changing the extraction page itself
- Analytics on shortcut clicks
- Conditional display based on user permissions
