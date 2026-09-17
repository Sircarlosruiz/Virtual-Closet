---
id: 005-usage-recording
unit: 001-image-generation-service
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 044-generation-reliability
implemented: false
---

# Story: 005-usage-recording

## User Story

**As a** platform operator
**I want** per-job usage information
**So that** platform OpenAI consumption can be monitored.

## Acceptance Criteria

- [ ] Given a provider response with usage, when the job completes, then model, calls and usage are stored.
- [ ] Given no provider usage, when the job completes, then usage is recorded as unknown rather than zero.
- [ ] Given a job, when viewed by authorized staff, then usage is linked to actor, wholesaler and job without exposing the API key.

## Technical Notes

- Cost estimates, if added later, must be labeled estimates.

## Dependencies

### Requires
- 003-provider-invocation-history

### Enables
- None

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Provider changes usage schema | Preserve raw safe fields and mark unsupported values unknown |

## Out of Scope

- Charging or invoicing wholesalers.
