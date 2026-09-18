---
id: 003-deterministic-sku-composition
unit: 002-template-composition-service
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 046-template-composition
implemented: true
---

# Story: 003-deterministic-sku-composition

## User Story

**As a** staff member
**I want** the SKU overlay rendered exactly after AI generation
**So that** product references are reliable and readable.

## Acceptance Criteria

- [ ] Given a generated base image and configured SKU, when composed, then the exact complete text is rendered at the configured position/style.
- [ ] Given an SKU/style change, when recomposed, then a new version is created without another OpenAI call or mutation of the base.
- [ ] Given an overlay that does not fit, when composed, then publication is blocked with a validation error.

## Technical Notes

- Preserve prior published versions; selected publication is handled by integration.

## Dependencies

### Requires
- 001-template-lifecycle, 002-composition-snapshot

### Enables
- 003-product-link-publication

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| SKU contains unsupported control characters | Reject or normalize according to documented validation |

## Out of Scope

- QR/barcode rendering.
