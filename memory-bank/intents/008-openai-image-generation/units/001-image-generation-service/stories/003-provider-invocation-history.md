---
id: 003-provider-invocation-history
unit: 001-image-generation-service
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 044-generation-reliability
implemented: false
---

# Story: 003-provider-invocation-history

## User Story

**As a** staff member
**I want** to see job status, attempts, inputs and provider errors
**So that** I can review and retry work without losing history.

## Acceptance Criteria

- [ ] Given a queued job, when the worker processes it, then status transitions are persisted as queued, processing, completed or failed.
- [ ] Given a provider error, when the retry policy applies, then attempts and reason are visible and no secret is stored.
- [ ] Given a completed job, when queried, then its durable result and configuration reference are available for review.

## Technical Notes

- Persist provider/model, actor, tenant, inputs, timestamps and error classification.

## Dependencies

### Requires
- 001-staff-provider-selection, 002-staff-generation-jobs

### Enables
- 004-generation-form

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Worker restarts | Job remains recoverable from database/queue |
| Provider returns no image | Job fails with explicit no-result reason |

## Out of Scope

- Visual quality scoring.
