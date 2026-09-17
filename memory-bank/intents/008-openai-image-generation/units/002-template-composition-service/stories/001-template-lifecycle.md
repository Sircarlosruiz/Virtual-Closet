---
id: 001-template-lifecycle
unit: 002-template-composition-service
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 045-template-lifecycle
implemented: true
---

# Story: 001-template-lifecycle

## User Story

**As a** staff member
**I want** to create common and wholesaler-private templates
**So that** product imagery follows reusable visual rules.

## Acceptance Criteria

- [ ] Given staff authorization, when a template is saved, then its scope, version, optional fields and references are persisted.
- [ ] Given a private template, when selected, then only the assigned wholesaler's products can use it.
- [ ] Given an archived template, when a new job selects it, then selection is rejected while historical snapshots remain readable.

## Technical Notes

- Staff administration is owned by Virtual Closet in V1.

## Dependencies

### Requires
- 001-staff-provider-selection

### Enables
- 002-composition-snapshot, 003-template-selection-ui

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Template references deleted | New selection requires replacement; historical result remains intact |

## Out of Scope

- Wholesaler-created templates.
