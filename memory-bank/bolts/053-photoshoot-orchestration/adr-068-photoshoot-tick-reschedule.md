---
bolt: 053-photoshoot-orchestration
created: 2026-09-19T15:58:00Z
status: proposed
superseded_by: null
---

# ADR-068: Photoshoot Orchestration Uses Tick + Celery Reschedule

## Context

A photoshoot waits on tryoff and on M PoseSets. Those jobs take minutes and already run on their own queues (`tryoff`, `vton`). The orchestrator must observe them, materialize completed slots, and derive aggregate status without hanging in `running`.

Two failure modes are well known in this repo:

- Blocking inside a Celery task for the whole wait occupies a worker and fights `time_limit`. ADR-065 rejected in-task `BLPOP` for that reason on the provider path.
- A single long `photoshoot_run` task that polls in a loop has the same shape: `time_limit` would have to cover tryoff + M×N Replicate calls, which is unbounded relative to one provider timeout.

ADR-065 is specifically the **global provider cap**. It does not define how a *parent* workflow waits on *child* jobs. Bolt 054 will keep ticking the same aggregate for status/idempotency; the wait pattern must be written down.

Celery messages may only carry identifiers (ADR-047). Commit the `queued` row before first publish (ADR-048 / ADR-005).

## Decision

Drive the pipeline with one idempotent task, `photoshoot_tick_task(photoshoot_id)`, on a dedicated **`photoshoot`** queue:

1. Load the aggregate. If status is terminal (`completed` | `partial` | `failed`), return.
2. `OrchestrationService.tick`: start missing delegated work, **observe child jobs via Postgres** (no Replicate calls), materialize ready slots, derive status.
3. If work remains, re-enqueue the same task with `countdown = PHOTOSHOOT_TICK_COUNTDOWN_SECONDS`.
4. If terminal, do not reschedule.

The broker payload is only `photoshoot_id`. Idempotency is `PhotoshootStage` status + `external_refs` + `UNIQUE(photoshoot_id, model_id, pose_id)`. A redelivered tick must not submit a second PoseSet or a second `GenerationJob` for an existing slot.

A tick does a bounded amount of work (one stage advance and/or materialize slots already complete). It does not sit in a sleep loop.

This does **not** replace ADR-065. Child VTON/tryoff workers still acquire the global slot. The photoshoot worker never holds that slot.

## Rationale

The scarce resource on the photoshoot worker is **process time**, not a Replicate slot. Reschedule returns the worker to the pool between observations, keeps `time_limit` small, and survives process restart the same way ADR-065 waiters do.

A dedicated queue (precedent: ADR-004 `tryoff`) keeps tick prefetch from starving inference workers and vice versa.

Polling child tables is the integration style already used by batch completion (ADR-008 callbacks update Postgres; readers observe rows). The photoshoot tick is that reader on a timer.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Tick + countdown reschedule (chosen) | Short tasks; restart-safe; ids only; reuse 065 intuition | Extra publishes; needs max-tick safety | Selected |
| Block / poll inside one task | Fewer messages | Holds a worker for minutes; `time_limit` vs NFR-3 | Same defect ADR-065 rejected |
| Celery chord/chain across tryoff + M PoseSets | Graph in the broker | Fragile across existing queues; payloads grow; hard to resume after worker death | Cross-queue orchestration is worse than DB observation |
| Callbacks injected into tryoff/vton tasks | Faster wake-up | Edits foreign tasks (ADR-008-style) and couples domains | 053 must not modify those pipelines |
| HTTP request runs the pipeline | No new queue | Violates NFR-1 p95 ≤ 1 s | Forbidden |

## Consequences

### Positive

- Submit stays a fast 202 (commit + first tick publish).
- Worker restart resumes from persisted stage/`external_refs`/slots.
- 054 can keep using the same task for later retries without a second orchestrator.

### Negative

- Progress is quantized by `countdown` (seconds of extra latency vs an in-process wait).
- A stuck child job needs `PHOTOSHOOT_MAX_TICKS` / derive-to-failed so the aggregate cannot run forever.

### Risks

- **Risk**: Tick storm if `countdown` is 0 or a bug always reschedules terminals. **Mitigation**: default countdown ≥ 2 s; exit when derived status is terminal; cap ticks and persist `error_code`.
- **Risk**: Two overlapping ticks on the same id. **Mitigation**: short transactions; conditional stage updates; slot UNIQUE (loser replays).

## Related

- **Stories**: 002-stage-pipeline-execution, 003-generation-job-materialization
- **Standards**: Celery task `time_limit`, broker payloads
- **Previous ADRs**: ADR-004, ADR-005, ADR-008, ADR-047, ADR-048, ADR-065, ADR-066
