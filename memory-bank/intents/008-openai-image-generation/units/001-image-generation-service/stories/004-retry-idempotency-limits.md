---
id: 004-retry-idempotency-limits
unit: 001-image-generation-service
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 044-generation-reliability
implemented: false
---

# Story: 004-retry-idempotency-limits

## User Story

**As a** platform operator
**I want** safe retries, idempotency and concurrency limits
**So that** API costs and duplicate images remain controlled.

## Acceptance Criteria

- [ ] Given the same idempotency key and payload, when submitted repeatedly, then one job is returned.
- [ ] Given duplicate delivery while an attempt is running, when consumed, then no concurrent provider call is started.
- [ ] Given a 429, when retrying, then at most two retries respect `Retry-After`; other non-transient errors do not auto-retry.

## Technical Notes

- Timeout with unknown provider outcome requires explicit retry, not blind duplication.

## Dependencies

### Requires
- 002-staff-generation-jobs, 003-provider-invocation-history

### Enables
- 003-integration-delivery, 005-usage-recording

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Same key, changed payload | Conflict response |
| Queue exceeds concurrency | Job remains queued and exposes queue time |

## Out of Scope

- Commercial billing or user-facing quotas.
