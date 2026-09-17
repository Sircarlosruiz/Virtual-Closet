---
id: 001-product-generation-bridge
unit: 003-product-image-integration
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 047-product-generation-bridge
implemented: false
---

# Story: 001-product-generation-bridge

## User Story

**As a** staff member
**I want** to start generation from a BFashion product or Virtual Closet
**So that** the same central workflow serves both applications.

## Acceptance Criteria

- [ ] Given an authorized staff request from either application, when product and wholesaler links are valid, then Virtual Closet creates the job.
- [ ] Given an unknown, mismatched or unauthorized product link, when requested, then the operation fails closed without generating or publishing.
- [ ] Given a BFashion-originated job, when status is requested, then the initiating UI can retrieve its Virtual Closet job state.

## Technical Notes

- Use authenticated server-to-server calls; never infer ownership from SKU alone.

## Dependencies

### Requires
- 002-composition-snapshot, 003-provider-invocation-history

### Enables
- 002-publication-selection, 003-sync-delivery

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| BFashion is unavailable | Job remains in Virtual Closet and sync state is retryable |

## Out of Scope

- Product price or inventory synchronization.
