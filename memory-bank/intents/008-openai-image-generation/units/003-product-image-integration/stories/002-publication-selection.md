---
id: 002-publication-selection
unit: 003-product-image-integration
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 048-product-publication-sync
implemented: false
---

# Story: 002-publication-selection

## User Story

**As a** staff member
**I want** to preview and select generated images
**So that** only approved imagery enters a product gallery.

## Acceptance Criteria

- [ ] Given completed results, when staff selects some and rejects others, then only selected results become publication candidates.
- [ ] Given an existing gallery, when a candidate is published, then existing images are not replaced automatically.
- [ ] Given a candidate, when staff changes the SKU composition, then the new version requires a new explicit selection.

## Technical Notes

- Selection is separate from generation completion.

## Dependencies

### Requires
- 001-product-generation-bridge, 003-deterministic-sku-composition

### Enables
- 003-sync-delivery

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Staff discards a result | It remains historical but cannot publish |

## Out of Scope

- Automatic publishing.
