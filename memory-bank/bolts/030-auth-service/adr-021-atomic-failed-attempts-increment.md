---
adr: 021
bolt: 030-auth-service
created: 2026-06-10T00:00:00Z
status: accepted
---

# ADR-021: Atomic Failed Attempts Increment for Account Lockout

## Context

Account lockout after 5 failed login attempts must be enforced even under concurrent login attempts. If a user submits multiple login requests simultaneously (or an attacker sends parallel requests), a naive read-increment-write pattern could result in lost updates, allowing more than 5 attempts before lockout.

## Decision

Use PostgreSQL's atomic UPDATE with expression evaluation to increment the `failed_attempts` counter:

```sql
UPDATE mayorista
SET failed_attempts = failed_attempts + 1,
    is_locked = (failed_attempts + 1 >= 5)
WHERE id = :user_id
RETURNING failed_attempts, is_locked
```

In SQLAlchemy async:
```python
stmt = (
    update(Mayorista)
    .where(Mayorista.id == user_id)
    .values(
        failed_attempts=Mayorista.failed_attempts + 1,
        is_locked=(Mayorista.failed_attempts + 1 >= 5),
    )
    .returning(Mayorista.failed_attempts, Mayorista.is_locked)
)
result = await db.execute(stmt)
row = result.first()
```

PostgreSQL's row-level locking guarantees that concurrent UPDATEs to the same row are serialized, preventing lost updates.

## Rationale

- **Correctness**: PostgreSQL guarantees atomicity of UPDATE expressions — no race conditions
- **Performance**: Single round-trip to the database; no separate SELECT needed
- **Simplicity**: No application-level locking or optimistic retry needed
- **PostgreSQL strength**: Leverages PostgreSQL's MVCC and row-level locking

## Consequences

- **Positive**: Guaranteed correct behavior under concurrency; no application-level complexity
- **Negative**: Requires PostgreSQL-specific behavior (though standard SQL supports this pattern)
- **Risk**: None — this is a well-established PostgreSQL pattern
- **Note**: The `is_locked` flag is set in the same statement, ensuring lockout happens exactly at the 5th attempt
