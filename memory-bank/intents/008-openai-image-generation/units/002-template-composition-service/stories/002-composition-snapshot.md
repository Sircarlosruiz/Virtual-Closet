---
id: 002-composition-snapshot
unit: 002-template-composition-service
intent: 008-openai-image-generation
status: complete
priority: must
created: 2026-09-17T01:23:26.000Z
assigned_bolt: 045-template-lifecycle
implemented: true
---

# Story: 002-composition-snapshot

## User Story

**As a** staff member
**I want** each result to retain the exact template/configuration snapshot
**So that** a later regeneration is explainable and reproducible.

## Acceptance Criteria

- [ ] Given a generation with a template, when accepted, then model, background, colors, rack, prompt, references, provider and version are snapshotted.
- [ ] Given a historical result, when its template is edited or archived, then its snapshot remains unchanged.
- [ ] Given a snapshot, when regenerated, then a new job/result is created without overwriting the original.

## Technical Notes

- Snapshot references must be durable storage keys, not temporary URLs only.

## Dependencies

### Requires
- 001-template-lifecycle, 002-staff-generation-jobs

### Enables
- 003-product-link-publication

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Historical reference missing | Block regeneration with actionable error |

## Out of Scope

- Automatic product publication.
