---
intent: 006-multi-pose-vton-generation
created: 2026-07-17T00:00:00Z
completed: 2026-07-17T00:00:00Z
status: complete
---

# Inception Log: 006-multi-pose-vton-generation

## Overview

**Intent**: Attach multiple pose photos to a mayorista's model and generate VTON output for a garment across all poses in one action, grouped as a pose set.
**Type**: green-field (new capability, builds on existing model upload + batch pipeline)
**Created**: 2026-07-17

## Artifacts Created

| Artifact | Status | File |
|----------|--------|------|
| Requirements | ✅ | requirements.md |
| System Context | ✅ | system-context.md |
| Units | ✅ | units/{unit-name}/unit-brief.md |
| Stories | ✅ | units/{unit-name}/stories/*.md |
| Bolt Plan | ✅ | memory-bank/bolts/028-032-*/bolt.md |

## Summary

| Metric | Count |
|--------|-------|
| Functional Requirements | 7 |
| Non-Functional Requirements | 3 |
| Units | 3 |
| Stories | 9 |
| Bolts Planned | 5 |

## Units Breakdown

| Unit | Stories | Bolts | Priority |
|------|---------|-------|----------|
| 001-model-pose-service | 4 | 2 | Must |
| 002-pose-set-service | 2 | 1 | Must |
| 003-multi-pose-vton-generation-ui | 3 | 2 | Must |

## Decision Log

| Date | Decision | Rationale | Approved |
|------|----------|-----------|----------|
| 2026-07-17 | Pose source limited to mayorista-uploaded models, small fixed set (~3-5 poses) | Keeps scope bounded; curated library multi-pose deferred | Yes |
| 2026-07-17 | Multi-pose generation built on existing BatchJob pipeline (005) rather than a new job type | Reuse proven batch infra instead of parallel execution path | Yes |
| 2026-07-17 | Pose outputs grouped as a linked "pose set" in media library/catalog UI | Lets mayorista use multi-angle outputs as one unit | Yes |
| 2026-07-17 | New `Model` aggregate introduced above existing `ModelPhoto`, which owns 1..N poses | Existing `ModelPhoto` conflates photo and model identity; grouping requires a real parent entity | Yes |
| 2026-07-17 | Pose type fixed enum `{front, side, back}`; mayorista can deselect poses before submitting | Bounded scope; avoids forcing generation on unwanted angles | Yes |
| 2026-07-17 | `PoseSet` is a new aggregate, 1:1 with `BatchJob`, created atomically at submission | Makes multi-pose results queryable as a group without new job-execution logic | Yes |
| 2026-07-17 | Requirements approved as drafted (Checkpoint 2) | User confirmed FR-1..FR-7 and NFRs capture intent | Yes |
| 2026-07-17 | Decomposed into 3 units: model-pose-service, pose-set-service, multi-pose-vton-generation-ui | Mirrors the two new bounded contexts (Model/pose grouping, PoseSet coordination) plus the standard frontend unit | Yes |
| 2026-07-17 | Artifacts (context, units, stories, bolt plan) approved as generated (Checkpoint 3) | User confirmed the breakdown, no changes requested | Yes |

## Scope Changes

| Date | Change | Reason | Impact |
|------|--------|--------|--------|

## Ready for Construction

**Checklist**:
- [x] All requirements documented
- [x] System context defined
- [x] Units decomposed
- [x] Stories created for all units
- [x] Bolts planned
- [x] Human review complete

## Next Steps

1. Begin Construction Phase
2. Start with Unit: `001-model-pose-service`
3. Execute: `/specsmd-construction-agent --unit="001-model-pose-service"`

## Dependencies

Depends on `001-vton-generation-pipeline` (model upload) and `005-batch-vton-generation` (BatchJob pipeline) for underlying infrastructure.
