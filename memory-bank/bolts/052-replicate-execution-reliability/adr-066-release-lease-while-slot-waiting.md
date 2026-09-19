---
bolt: 052-replicate-execution-reliability
created: 2026-09-19T01:44:22Z
status: proposed
superseded_by: null
---

# ADR-066: Release the Per-Job Lease While Waiting for a Global Slot

## Context

The domain model for bolt 052 ordered worker steps as: credential gate → per-job lease (ADR-050) → global slot (ADR-065) → provider call. The intent of "lease before slot" was to avoid occupying a scarce global slot when a duplicate delivery cannot run.

ADR-050's lease is held until the worker releases it. If the worker holds the lease for the entire slot wait, two failures appear:

1. **Orphaned lease on waiter death.** ADR-050 already notes that a crash while the lease is held blocks the job until reconciliation. Slot waits can last tens of minutes (12 jobs, cap 2, multi-minute Replicate calls). A restart during wait would look like "lease held" to the redelivered task, which then exits with no provider call — the duplicate-delivery safeguard firing on a *waiter*, not a duplicate.
2. **Heartbeat complexity.** Keeping the lease across a long wait would require refreshing `locked_at` for the whole delay, extending ADR-050 beyond "mutual exclusion for an in-flight call".

ADR-065 already chose non-blocking acquire + Celery reschedule, so the wait is not inside a single task execution. The lease must have a defined home across those reschedules.

## Decision

**Hold the per-job lease only while a global slot is held or a provider call is in flight. Release the lease before rescheduling a slot wait.**

Effective order:

1. Credential gate (no lease, no slot, no network).
2. `try_acquire` lease. If denied (held and not stale) → exit; this is a true duplicate delivery.
3. `try_acquire` global slot. If denied → **release lease**, record `concurrency_wait_started_at` once, reschedule, return.
4. Slot acquired → record call start, invoke provider, release slot, release lease.

A duplicate delivery that arrives while the holder is *in flight* still fails the lease and does not call the provider. A waiter never retains the lease between countdown ticks.

This does not change ADR-050's storage or acquire/release primitive. It only shortens the hold interval so it matches "I am the worker executing this job now", not "I am waiting for permission to execute".

## Rationale

The scarce resource during wait is the *slot*, not the lease. Holding the lease while waiting converts a restart-safe reschedule (ADR-065) into a stuck job. Releasing the lease makes redelivery a normal acquire again.

A wasted slot on a true duplicate is avoided by acquiring the lease *before* the slot on each attempt, then releasing both if the slot is denied. The window where a duplicate could take a slot and then fail the lease is one attempt, and that attempt releases the slot in the same task.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Hold lease for the entire wait (literal domain order) | Duplicate never waits | Waiter crash orphans the job for minutes; needs heartbeat | Restart hazard larger than the slot-waste it prevents |
| Slot first, then lease | Waiter death holds neither | Duplicate waiters can consume slots until they fail the lease | Wastes the scarce cap under duplicate delivery |
| Heartbeat `locked_at` while waiting | Keeps lease-before-slot story | Extends ADR-050; still holds exclusion during a wait that is no longer in-process after ADR-065 | Unnecessary once wait is a reschedule |
| Release lease on slot deny (selected) | Redelivery works; lease still gates the actual call; no ADR-050 schema change | Two acquires per wait tick | Selected |

## Consequences

### Positive

- Worker restart during a slot wait does not stick the job behind an orphaned lease.
- ADR-050 remains the duplicate-delivery guard for in-flight calls only, which is what it was designed for.
- Queue wait can last as long as ADR-065 allows without a lease TTL/heartbeat project.

### Negative

- Each countdown tick re-acquires the lease. Under a burst of duplicate deliveries, several tasks may briefly contend on `lock_token` before one holds both lease and slot.

### Risks

- A duplicate could theoretically win a slot on the same tick the holder released it after a deny. Mitigation: Lua acquire is per `job_id` and idempotent for the holder; the duplicate still needs the lease. If it wins the lease, it *is* the executor for that tick — correct, not a double call.

## Related

- **Stories**: 002-provider-credential-gating, 003-global-concurrency-cap
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: ADR-049, ADR-050, ADR-065
