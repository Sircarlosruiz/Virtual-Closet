---
bolt: 053-photoshoot-orchestration
created: 2026-09-19T15:58:00Z
status: proposed
superseded_by: null
---

# ADR-070: Materialized Results Own a Copy Under `generated/photoshoots/...`

## Context

FR-7 requires each photoshoot cell (model × pose) to become a `GenerationJob` with `status = completed` and a durable `result_key` in the `generated` bucket, so `publication_service.list_candidates` and `POST .../publications` work without code changes.

PoseSet / batch store result media on `BatchItem` / media-library rows. Those objects are owned by the batch/media lifecycle (retry, re-save, mayorista deletes). If the photoshoot `GenerationJob` only *referenced* that key, a later media delete or overwrite would break a publication candidate and violate NFR-5 (“a BFashion sync failure must not lose a result already generated here” — the inverse also holds: a batch-library change must not unpublish our carrier).

NFR-5 also says: if persist to object storage fails, the job is **not** marked completed; retry persist **without** calling the provider again.

## Decision

On materialize, **copy** the produced image to a photoshoot-owned key:

```text
generated/photoshoots/{photoshoot_id}/{model_id}/{pose_id}
```

`GenerationJob.result_key` points at **that** key, never at the batch/media key as the source of truth.

Rules:

1. Copy (or server-side object copy) from the child result to the photoshoot key.
2. Only after the object exists, create/complete the `GenerationJob` via `GenerationJobRepository` and insert `PhotoshootResult`.
3. `UNIQUE(photoshoot_id, model_id, pose_id)` is the slot lock. A second tick that loses the insert replays; it does not write a second job or a second copy as a new identity.
4. If the copy fails: no `completed` job. The next tick retries the copy only.
5. Two poses that happen to be byte-identical still get two keys and two jobs (no content hash dedup).

Do not modify `publication_service.py` or `sync_delivery_service.py`. The existing reader already follows `result_key`.

## Rationale

The publication path is built on “this job owns this object”. Sharing a batch key couples two aggregates and makes retention undefined. A copy is cheap relative to Replicate and gives the photoshoot a stable artifact for FR-13 / later regeneration.

Server-side copy (when the provider supports it) avoids pulling bytes through the worker. If only GET+PUT is available, still copy; do not skip.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Copy to photoshoot key (chosen) | Independent retention; `result_key` is ours | Extra storage; copy can fail and needs retry | NFR-5 |
| Reuse BatchItem / media key | No copy | Candidate dies if media is deleted/overwritten; ownership unclear | Fails durability |
| Dedup by content hash | Less storage | Story 003 forbids merging two slots | Explicitly out of scope |
| Complete the job then copy | Job appears earlier | `completed` without `result_key` is forbidden | Invariant |

## Consequences

### Positive

- Publication candidates survive batch-library churn.
- Persist retry is a storage operation, not a provider call.
- Key layout is guessable for ops (`photoshoot_id` in the path) without being a public URL.

### Negative

- N×M extra objects. Acceptable vs inference cost.
- Copy adds a failure mode that ticks must handle.

### Risks

- **Risk**: Implementers set `result_key` to the batch key “temporarily”. **Mitigation**: Stage 5 asserts the prefix `generated/photoshoots/{photoshoot_id}/`; publication-candidate tests use that key.

## Related

- **Stories**: 003-generation-job-materialization
- **Standards**: MinIO key layout for generated assets
- **Previous ADRs**: ADR-010, ADR-011, ADR-047
