---
id: 001-generation-form
unit: 004-openai-generation-ui
intent: 008-openai-image-generation
status: draft
priority: must
created: 2026-09-17T01:23:26Z
assigned_bolt: 049-openai-generation-ui
implemented: false
---

# Story: 001-generation-form

## User Story

**As a** staff member
**I want** one interface for the four generation modes
**So that** I can provide only the inputs required by the selected mode.

## Acceptance Criteria

- [ ] Given staff access, when a mode is selected, then the form shows its required and optional inputs and provider choices.
- [ ] Given invalid/missing input, when submitted, then the form explains the issue without creating a job.
- [ ] Given a request from BFashion, when opened, then product and wholesaler context is visible and preserved.

## Technical Notes

- Backend remains source of truth for authorization and validation.

## Dependencies

### Requires
- 001-staff-provider-selection, 002-staff-generation-jobs

### Enables
- 002-generation-review

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Non-staff user opens route | No generation controls and no data leakage |

## Out of Scope

- Direct OpenAI calls from browser.
