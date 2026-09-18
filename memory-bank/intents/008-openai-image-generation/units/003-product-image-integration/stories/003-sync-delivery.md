---
id: 003-sync-delivery
unit: 003-product-image-integration
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 048-product-publication-sync
implemented: true
---

# Story: 003-sync-delivery

## User Story

**As a** staff member
**I want** selected images and configuration synchronized to both product systems
**So that** Virtual Closet and BFashion show the same approved result.

## Acceptance Criteria

- [ ] Given an explicit selection, when delivery succeeds, then both destinations store the image and configuration snapshot.
- [ ] Given duplicate delivery or retry, when processed, then no duplicate ProductImage or generation is created.
- [ ] Given a failed destination, when viewed, then it shows failed/retryable without marking the other destination incorrectly.

## Technical Notes

- BFashion currently has `ProductImage`; its configuration persistence and contract require a cross-repo design.

## Dependencies

### Requires
- 001-product-generation-bridge, 002-publication-selection

### Enables
- 004-product-integration-ui

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Temporary transfer URL expires | Use durable storage reference or refresh transfer without regenerating |

## Out of Scope

- Catalog publication status beyond product gallery synchronization.
