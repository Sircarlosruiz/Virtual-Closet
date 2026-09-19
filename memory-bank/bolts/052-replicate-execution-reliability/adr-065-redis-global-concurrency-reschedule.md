---
bolt: 052-replicate-execution-reliability
created: 2026-09-19T01:44:22Z
status: proposed
superseded_by: null
---

# ADR-065: Redis Semaphore + Celery Reschedule for the Global Provider Cap

## Context

NFR-2 requires a deployment-wide cap on simultaneous calls to the image-generation provider. `ConcurrencyGuardService` (ADR-050) is a per-job lease: it prevents duplicate delivery of *one* job from starting two calls. It does not limit how many *distinct* jobs call the provider at once. A photoshoot that expands to 12 results must complete all 12, never exceed the cap (starting proposal: 2), and must not fail the excess work — it waits.

Two candidate backings were named in inception: a Redis semaphore (`REDIS_URL` already exists) or a RabbitMQ prefetch cap (`worker_prefetch_multiplier`). How waiters wait also matters: blocking inside the Celery task (`BLPOP`) occupies a worker for the entire queue delay and fights `time_limit`, which must stay sized to the Replicate call (minutes), not to an unbounded wait.

ADR-050 explicitly rejected Redis for the *per-job* lease because that lease is 1:1 with a `generation_jobs` row. This decision must not reopen that choice.

## Decision

Implement the global cap as a **non-blocking Redis SET semaphore** plus **Celery reschedule**:

- SET `imggen:global_in_flight` holds `job_id`s currently calling the provider.
- `try_acquire(job_id, cap)` is a Lua script: idempotent if the job already holds a slot; otherwise `SADD` only when `SCARD < cap`.
- A TTL key `imggen:slot:{job_id}` (timeout + 60s) recovers slots if a holder crashes.
- If acquire is denied, the task **does not fail**. It re-enqueues `generate_image_task(job_id)` with `countdown` and returns. This path does **not** increment provider `retry_count` and does **not** write a `ProviderInvocation`.
- If Redis is unavailable, fail closed: do not call the provider (do not skip the cap). Reschedule as if the pool were full.

The per-job lease stays on Postgres (`lock_token` / `locked_at`). Redis is only the global pool.

`IMAGE_GENERATION_GLOBAL_CONCURRENCY` is a deployment setting, `>= 1`, default 2 (OQ-3). Invalid values fail process startup, not a running job.

## Rationale

The cap is a deployment-wide, ephemeral count. It is not 1:1 with a Postgres row, so the ADR-050 reason to keep the lease in Postgres does not apply. Redis is already the cross-worker coordination store for ephemeral state (ADR-016/023/027).

RabbitMQ prefetch is per-worker. `prefetch × worker_count` cannot guarantee a global `in_flight ≤ 2` when more than one worker is up, and changing replica count would silently change the cap.

Blocking inside the task (`BLPOP`) would hold a worker process for the whole wait (a 12-job / cap-2 / 10-minute-call burst can wait ~50 minutes) and would require a Celery `time_limit` larger than the provider timeout, breaking NFR-3's "size the limit to Replicate, then persist `timed_out` within 30s".

Reschedule leaves waiters in RabbitMQ: they survive worker restart, do not look like provider retries, and keep `time_limit` = Replicate timeout + buffer.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| RabbitMQ `worker_prefetch_multiplier` as the cap | No new Redis keys; simple ops | Cap is per worker, not global; replica count changes effective parallelism | Cannot satisfy NFR-2 |
| Redis `BLPOP` / blocking semaphore inside the task | True wait without extra enqueues | Occupies a worker for the whole queue delay; fights Celery `time_limit`; waiter crash while blocked is harder to reason about | Incompatible with minutes-long Replicate timeouts |
| Postgres counter table with polling | Single store with the job row | Workers would poll SQL while "waiting"; still need a wait strategy; mixes durable job state with ephemeral pool state | Worse fit than Redis for a cap that must not hold a transaction |
| Redis SET + Celery reschedule (selected) | Global cap, restart-safe wait, `time_limit` stays call-sized, lease stays in Postgres | Extra broker messages; depends on Redis availability (fail-closed) | Selected |

## Consequences

### Positive

- A photoshoot of 12 with cap 2 completes without discarding work and without exceeding two in-flight provider calls.
- ADR-050 remains intact: duplicate delivery of one job is still a Postgres lease.
- Celery `time_limit` can stay `REPLICATE_TIMEOUT + 60s` so `timed_out` is persisted within 30s (NFR-3, ADR-049).

### Negative

- Slot wait produces additional Celery messages (one per `countdown` tick).
- Redis is now on the inference path, not only auth. An outage delays generation (fail-closed) instead of lifting the cap.

### Risks

- A crashed holder could leak a slot. Mitigation: TTL key + purge of members whose TTL is gone on each acquire.
- Slot-wait retries could be confused with provider retries. Mitigation: dedicated reschedule path; never increment `retry_count` or write an invocation row.
- Pathological pool stall. Mitigation: `IMAGE_GENERATION_SLOT_WAIT_MAX_SECONDS` (default 6h) then `GLOBAL_CONCURRENCY_WAIT_EXHAUSTED`.

## Related

- **Stories**: 003-global-concurrency-cap, 004-provider-timeout-policy
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: ADR-016, ADR-023, ADR-027, ADR-049, ADR-050
