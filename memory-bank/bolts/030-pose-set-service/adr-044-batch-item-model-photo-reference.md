---
bolt: 030-pose-set-service
created: 2026-07-18T06:47:24Z
status: accepted
superseded_by: null
---

# ADR-044: Store ModelPhoto IDs in Pose-Set Batch Items

## Context

The existing BatchItem field is named `model_id`, but VTON execution consumes a
model-photo record. PoseSet needs to map each completed item back to its pose
type without adding another mapping table or changing BatchItem schema.

## Decision

For PoseSet submissions, `BatchItem.model_id` stores the selected
`ModelPhoto.id`. The PoseSet service validates the ID against the requested
parent Model and mayorista before delegating batch creation. Result projection
joins BatchItem.model_id to ModelPhoto.id and reads `ModelPhoto.pose`.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| New BatchItem pose FK | Explicit naming | Schema change and batch-domain modification | Violates reuse constraint |
| Separate PoseSetItem mapping table | Clear separation | Extra rows, joins, and atomicity surface | Duplicates existing one-item-per-pose relationship |
| Existing `BatchItem.model_id` (chosen) | Zero schema changes; compatible with VTON input path; direct result mapping | Field name is semantically broad | Existing implementation already treats it as a ModelPhoto input |

## Consequences

### Positive

- Existing batch execution receives the exact selected photo IDs
- Pose lookup remains deterministic through ModelPhoto.pose
- No changes to BatchJob/BatchItem persistence or workers

### Negative

- Documentation must clarify that this field refers to ModelPhoto IDs
- Generic batch consumers must preserve existing model-photo semantics

### Risks

- Future code may assume `model_id` references a parent Model. Mitigation: add explicit repository/service documentation and integration tests.

## Related

- **Stories**: 001-submit-pose-set, 002-view-pose-set-results
- **Previous ADRs**: ADR-012, ADR-039
