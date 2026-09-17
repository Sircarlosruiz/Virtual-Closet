---
id: 001-staff-provider-selection
unit: 001-image-generation-service
intent: 008-openai-image-generation
status: complete
priority: must
created: '2026-09-17T01:23:26Z'
assigned_bolt: 043-image-generation-service
implemented: true
---

# Story: 001-staff-provider-selection

## User Story

**As a** staff member
**I want** to choose OpenAI or the existing VTON provider for model try-on
**So that** I can use the appropriate generation capability without exposing credentials.

## Acceptance Criteria

- [ ] Given an authorized staff request, when a supported provider is selected, then the job stores that provider.
- [ ] Given a browser or BFashion request, when it submits a job, then the OpenAI key is never returned or logged.
- [ ] Given an unsupported provider/mode combination, when submitted, then the request is rejected before inference.

## Technical Notes

- Extend provider selection without breaking `VTONProvider`.
- Read platform credential only in the backend worker/service.

## Dependencies

### Requires
- None

### Enables
- 001-staff-generation-jobs, 001-provider-invocation-history

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Missing OpenAI credential | Fail closed with actionable configuration error |
| Provider timeout | Persist failure/unknown result according to retry policy |

## Out of Scope

- Per-wholesaler API keys.
