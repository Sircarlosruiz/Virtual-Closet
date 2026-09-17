---
id: 002-staff-generation-jobs
unit: 001-image-generation-service
intent: 008-openai-image-generation
status: complete
priority: must
created: '2026-09-17T01:23:26Z'
assigned_bolt: 043-image-generation-service
implemented: true
---

# Story: 002-staff-generation-jobs

## User Story

**As a** staff member
**I want** to submit model try-on, text, edit and extraction jobs
**So that** the platform can generate reusable product imagery asynchronously.

## Acceptance Criteria

- [ ] Given valid inputs for each mode, when submitted, then a durable job id and queued status are returned.
- [ ] Given a try-on job, when garment/model inputs and cloth type are valid, then the job is accepted for the selected provider.
- [ ] Given text, edit or extraction input, when required prompt/reference validation passes, then OpenAI is queued without requiring a garment/model pair.

## Technical Notes

- Reuse Celery/RabbitMQ patterns and media references.
- One result per job in V1.

## Dependencies

### Requires
- 001-staff-provider-selection

### Enables
- 001-provider-invocation-history, 004-generation-form

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Empty prompt | Validation error before enqueue |
| Missing required mode input | Validation error naming the missing input |

## Out of Scope

- Product publication and template administration.
