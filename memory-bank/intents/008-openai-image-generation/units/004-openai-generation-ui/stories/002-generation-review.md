---
id: 002-generation-review
unit: 004-openai-generation-ui
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 049-openai-generation-ui
implemented: true
---

# Story: 002-generation-review

## User Story

**As a** staff member
**I want** to monitor and compare generated results
**So that** I can accept, reject or recompose them with confidence.

## Acceptance Criteria

- [ ] Given a queued or processing job, when the page refreshes, then current state and actionable errors are shown.
- [ ] Given a completed result, when previewed, then source references, provider, template snapshot and SKU are distinguishable.
- [ ] Given a SKU/style change, when recomposed, then a new version is shown and the original remains available.

## Technical Notes

- Polling may reuse current job-status patterns; no browser secret.

## Dependencies

### Requires
- 003-provider-invocation-history, 003-deterministic-sku-composition

### Enables
- 003-product-integration-ui

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Result fails | Show reason and explicit retry path where allowed |

## Out of Scope

- Automatic quality scoring.
