---
bolt: 053-photoshoot-orchestration
created: 2026-09-19T15:58:00Z
status: proposed
superseded_by: null
---

# ADR-069: Contract-C `pose_ids` Are Pose Types, Resolved to ModelPhoto IDs Server-Side

## Context

FR-5 accepts `pose_ids` or `pose_count` on `POST .../photoshoots`. PoseSet’s internal contract takes `pose_ids` as **`ModelPhoto.id`** values stored on `BatchItem.model_id` (ADR-044).

The photoshoot-options catalog (bolt 056) does **not** expose `ModelPhoto.id`. It exposes `available_poses: ["front", "side"]` with canonical order `front < side < back` and `max_pose_count = 3`. BFashion’s staff form is built from that catalog (intent 020). If Contract C required photo UUIDs, the form would have no legal values unless 056 were reopened.

The domain also requires a **uniform cartesian product**: every selected model must cover the same pose set, or submit returns 422 and creates no row. `expected_results` is frozen at accept time as `|models| × |poses|`.

## Decision

On Contract C, `pose_ids` is a list of **pose types** from the closed set `{front, side, back}`, not `ModelPhoto` UUIDs.

Resolution happens in `PhotoshootSubmissionService` **before** persist:

1. If both `pose_ids` and `pose_count` are present → 422.
2. If neither is present → use `PHOTOSHOOT_DEFAULT_POSE_COUNT` (OQ-4, default 3).
3. `pose_count` / default selects the first N types in canonical order that **every** selected model actually has. If the common coverage is smaller than the requested count → 422 `POSE_SELECTION_INVALID`.
4. Explicit `pose_ids` must be a duplicate-free subset of `{front, side, back}`. Every selected model must have a `ModelPhoto` for each type → else 422.
5. The snapshot stores `pose_types` plus `resolved_poses[model_id] = [{pose, model_photo_id}, ...]`.
6. `PhotoshootResult.pose_id` and PoseSet submission use the **resolved `ModelPhoto.id`** (ADR-044 unchanged).
7. `tenant_id` is passed into PoseSet/batch (ADR-045).

Unknown strings, UUIDs-as-pose_ids, and empty lists after resolution are 422. No row, no enqueue.

## Rationale

The public C contract must match what BFashion can discover. The internal PoseSet contract stays photo-id based so batch/VTON input does not change.

Uniform coverage keeps `expected_results` honest. A per-model “best effort” count would make the 202 promise a lie for some models.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| C `pose_ids` = pose types (chosen) | Matches 056; form can submit what it listed | Name `pose_ids` is not a UUID list | Contract honesty > name purity |
| C `pose_ids` = `ModelPhoto.id` | Same name as PoseSet | Catalog does not expose those ids; 020 cannot comply | Would force a 056 reopen or embed ids in the form |
| Accept either UUIDs or types | Flexible | Ambiguous; existence oracles; tests fork | One rule |
| Per-model pose lists in the body | More precise | Breaks uniform `expected_results`; heavier C contract | V1 cartesian is enough |
| Change 056 to return photo UUIDs | Would allow UUID pose_ids | Couples catalog identity to batch internals; bigger surface | Not needed if the server resolves |

## Consequences

### Positive

- Intent 020 can send catalog values unchanged.
- ADR-044 remains the PoseSet rule; 053 is the translator.
- 422-before-enqueue holds when a model lacks a requested pose.

### Negative

- The field name `pose_ids` means types on C and photo ids internally. Docs and schemas must say so.
- Adding a fourth pose label later is a catalog + enum change, not “just another UUID”.

### Risks

- **Risk**: A client sends ModelPhoto UUIDs in `pose_ids`. **Mitigation**: enum validation; 422; OpenAPI examples use `front` / `side` / `back`.

## Related

- **Stories**: 001-photoshoot-submission, 002-stage-pipeline-execution
- **Standards**: Contract C request schemas next to photoshoot-options
- **Previous ADRs**: ADR-044, ADR-045, ADR-063 (catalog shape)
