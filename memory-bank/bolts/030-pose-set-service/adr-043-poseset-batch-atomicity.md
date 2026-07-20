---
bolt: 030-pose-set-service
created: 2026-07-18T06:47:24Z
status: accepted
superseded_by: null
---

# ADR-043: PoseSet and Batch Creation Share One Transaction

## Context

A pose-set submission creates grouping metadata and delegates execution records
to the existing BatchJob/BatchItem service. Committing either side separately
can leave a PoseSet without a batch or a batch that cannot be presented as a
PoseSet.

## Decision

Use one `AsyncSession` transaction for PoseSet validation, delegated
BatchJob/BatchItem creation, and PoseSet insertion. Flush for generated IDs,
then commit once. Roll back the session on any validation, persistence, or
delegated batch failure. Task publication remains governed by ADR-005/ADR-007
and occurs only through the existing batch path after the database commit.

## Rationale

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Separate PoseSet and batch commits | Simple composition | Creates orphaned or ungrouped records on partial failure | Violates story atomicity |
| New outbox/workflow for PoseSet | Strong recovery semantics | Duplicates existing batch infrastructure | Unnecessary for the bounded synchronous operation |
| Shared transaction (chosen) | No orphaned records; reuses existing transaction boundary | Requires internal service call to accept the caller's session | Correct minimal design |

## Consequences

### Positive

- PoseSet and batch metadata are all-or-nothing
- Existing task publication and retry behavior remain unchanged
- Failure tests can assert zero persisted records

### Negative

- The internal batch service must not commit independently
- PoseSet orchestration is coupled to the existing SQLAlchemy session contract

### Risks

- A future batch service change that commits internally could break atomicity. Mitigation: document and test the shared-session contract.

## Related

- **Stories**: 001-submit-pose-set, 002-view-pose-set-results
- **Previous ADRs**: ADR-005, ADR-007
