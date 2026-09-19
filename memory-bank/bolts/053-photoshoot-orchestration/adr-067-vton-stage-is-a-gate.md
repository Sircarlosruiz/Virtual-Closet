---
bolt: 053-photoshoot-orchestration
created: 2026-09-19T15:58:00Z
status: proposed
superseded_by: null
---

# ADR-067: Photoshoot VTON Stage Is a Validation Gate, Not a Billable Inference

## Context

Story 002 requires the `garment_on_model` pipeline to run `tryoff → vton → poses → composition` and to delegate to `TryoffJobService`, `VTONJobService`, `PoseSetService` / `BatchSubmissionService`, and `SkuCompositionService`.

`PoseSet.submit_pose_set` already expands one garment × one model × N poses into a `BatchJob` whose `BatchItem`s become `VtonJob`s (bolt 030, ADR-043/044). A photoshoot with M models therefore already produces M×N provider calls on the poses stage.

Reading “delegate to `VTONJobService`” as “enqueue `generate` once per model before PoseSet” would add M extra Replicate calls. Those calls are not publication candidates (only pose-stage images are materialized). They would compete for the deployment-wide cap (ADR-065, OQ-3, default 2), inflate cost, and still leave PoseSet to infer the same pairings again.

The domain model already named this step a **branch gate**: a model that cannot be paired is dropped; other models continue. It did not require a paid image.

## Decision

The `vton` `PhotoshootStage` **validates and binds** each living branch through `VTONJobService`’s input surface (garment exists, model is owned, `cloth_type` is accepted). It does **not** call `generate` and does **not** enqueue a billable `VtonJob`.

- Effective `garment_id` comes from tryoff (`garment_on_model`) or from the ready reservation’s registered media (`flat_garment`).
- A model that fails validation is a failed branch (`external_refs[i].status = failed`). Other branches continue.
- The `vton` stage is `completed` when every branch has a decision and at least one branch is alive; `failed` only when zero branches remain.
- PoseSet is the only photoshoot path that starts VTON inference.

If `VTONJobService` has no public `validate_pairing`, implementation reuses the **same validators** that service already runs before create/enqueue. It must not invent a second validation or a silent `generate`.

## Rationale

“Delegate” means use the existing service’s authority over pairings, not fire every method it owns. PoseSet is already the N-expansion engine; duplicating inference contradicts FR-6 (“do not reimplement / do not duplicate inference logic”) and NFR-2.

The four stage rows stay visible to BFashion (`skipped` / `pending` / `completed`). The `vton` row records that the pairing gate ran, which is what the `202.stages` contract needs.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Validate via VTONJobService, no generate (chosen) | One paid path (PoseSet); gate still uses the real pairing rules | Stage name `vton` does not mean “image produced” | Cost and cap beat literal generate |
| One full VTON per model, then PoseSet | Literal reading of “call VTONJobService” | M extra billable calls; double work; first pose may duplicate | Violates cost, cap, and “materialize only pose outputs” |
| Skip the vton stage entirely | Simpler | Fails story 002’s four-stage / VTONJobService criterion; no per-model fail-closed before N calls | Stage must exist; it does not have to infer |
| VTON first pose, PoseSet the rest | Slightly fewer extra calls | Split accounting; `expected_results` vs leftover poses is messy | Rejected in design |

## Consequences

### Positive

- M×N provider calls, not M + M×N.
- A bad model dies at the gate instead of opening a PoseSet.
- Stage 4 has an explicit “do not enqueue generate here” rule.

### Negative

- Reviewers must not “fix” the gate into a `generate` to make the stage name feel more literal.
- Requires a reusable validation entry on or beside `VTONJobService`.

### Risks

- **Risk**: PoseSet’s validators drift from the gate. **Mitigation**: share the same function; tests assert no Celery VTON publish during the vton stage.

## Related

- **Stories**: 002-stage-pipeline-execution, 003-generation-job-materialization
- **Standards**: Celery / provider cost on the inference path
- **Previous ADRs**: ADR-043, ADR-044, ADR-046, ADR-065
