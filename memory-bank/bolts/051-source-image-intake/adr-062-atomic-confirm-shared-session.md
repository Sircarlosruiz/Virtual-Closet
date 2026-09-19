---
bolt: 051-source-image-intake
created: 2026-09-19T01:48:00Z
status: proposed
superseded_by: null
---

# ADR-062: Atomic Confirm Registers Media in the Request Session

## Context

Confirm must make a reservation `ready` and record exactly one delegated media row (`SourceImage` or `GarmentPhoto`). Story 002 forbids a second media on replay or concurrent confirm. The unit forbids a fourth origin store: registration goes through `tryoff_source_image_service` or `media_service`.

Those media services today exist for cookie-auth uploads and may commit or flush on their own. If confirm calls them and then loses a race on `status`, or if they commit before the reservation update, we get an orphan media row or two registered origins for one `source_image_id`.

A service-layer "check ready then insert" is not enough: two requests can both see `pending`. ADR-010 / ADR-054 already made uniqueness/conditional writes the authority for idempotency. ADR-050 used a conditional `UPDATE` for a lease. Confirm needs the same class of guarantee across **two** tables in two bounded contexts.

## Decision

`confirm` of a `pending` row is one request transaction:

1. Authenticate, resolve staff, resolve the active `ProductLink`, load the owned reservation.
2. `SELECT … FOR UPDATE` the `bridge_source_images` row while `status = 'pending'` (or equivalent row lock).
3. Observe the object (`exists` / `head` / validate / optional checksum). Rejection updates `pending → rejected` in this same transaction and returns 409.
4. On success, call the media service **with the request `AsyncSession`**. The service must not commit, rollback, or open a second session.
5. Conditional `UPDATE … WHERE id = :id AND status = 'pending'` to `ready` with `registered_media_id` / `registered_media_kind` / `actual_*` / `confirmed_at`.
6. Commit once at the intake service / request boundary.

The loser of the race waits on the lock, then either sees `ready` and **replays** (same id, new preview URL, no second register) or sees `rejected` and returns 409. `MediaRegistrationGateway` is not invoked on replay.

If a media service cannot accept an injected session without a commit, adapt that service **minimally** so it can. Do not add a parallel origin table. Do not commit media first and "best-effort" the reservation.

Replay of an already-`ready` row skips the lock-register path: read, sign preview, return 200.

## Rationale

The reservation row is the lock. Media insertion is a side effect that must commit or vanish with it. Sharing the session is cheaper than outbox/saga for a synchronous, local write, and it keeps the "no fourth store" rule.

Conditional status transition remains the authority if a second writer sneaks in; the row lock makes the media call happen at most once under normal isolation.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Row lock + shared session (chosen) | One media; rollback is automatic; no new table | Media services must not self-commit | Matches stories and existing layering |
| Register media, then update status | Simple call order | Orphan media if the update loses or the process dies after a nested commit | Breaks "exactly one media" |
| Unique `(registered_media_id)` only | Cheap extra constraint | Does not prevent two media rows; only detects them | Detection ≠ prevention |
| Outbox / Celery to register later | Confirm stays tiny | `ready` without media, or `pending` after a successful PUT; 053 cannot fire | Confirm's contract is "usable now" |
| Fourth origin table owned by the bridge | Easy transaction | Forbidden by the unit; TryOff/VTON would not see the bytes | Product/unit constraint |

## Consequences

### Positive

- Concurrent confirms converge on one `RegisteredMediaRef`.
- Crash before commit leaves `pending` and no media — the client retries confirm.
- 053 can trust `ready` ⇒ media exists in the store `registered_media_kind` names.

### Negative

- Cookie-auth media services gain a "don't commit" contract when called from the bridge.
- Confirm holds a row lock across `HeadObject` + decode ≤ 10 MiB. Keep the lock section short; do not download the object twice.

### Risks

- **Risk**: A future helper in `media_service` calls `session.commit()`. **Mitigation**: intake tests with two overlapping confirms; code review treats a commit inside the gateway path as a defect.
- **Risk**: Decode + lock exceeds NFR-1. **Mitigation**: validate against the configured max; `HeadObject` first; reject empty/oversize before reading bytes.

## Related

- **Stories**: 002-source-image-confirm, 003-source-image-rejection
- **Standards**: Transaction boundary for delegated media writes
- **Previous ADRs**: ADR-010 (idempotency at the database), ADR-054 (deterministic uniqueness), ADR-050 (conditional UPDATE as lease), ADR-043 (shared session across aggregates)
