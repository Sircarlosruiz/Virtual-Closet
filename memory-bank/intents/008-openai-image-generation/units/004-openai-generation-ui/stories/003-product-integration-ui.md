---
id: 003-product-integration-ui
unit: 004-openai-generation-ui
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 049-openai-generation-ui
implemented: true
---

# Story: 003-product-integration-ui

## User Story

**As a** staff member
**I want** to select results and see synchronization state
**So that** I know exactly what was added to each product gallery.

## Acceptance Criteria

- [ ] Given completed results, when staff selects images, then the UI clearly distinguishes candidate, published and discarded states.
- [ ] Given a sync operation, when one destination succeeds and another fails, then each status is shown independently with retry action.
- [ ] Given a successful publish, when the product is reopened in either app, then the selected image and configuration are visible.

## Technical Notes

- Must support the Virtual Closet product view and BFashion admin entry contract.

## Dependencies

### Requires
- 002-publication-selection, 003-sync-delivery

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Duplicate retry | UI remains one gallery item with synchronized status |

## Out of Scope

- Wholesale customer generation controls.
