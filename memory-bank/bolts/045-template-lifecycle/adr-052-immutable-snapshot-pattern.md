---
bolt: 045-template-lifecycle
created: 2026-09-17T18:39:38Z
status: proposed
superseded_by: null
---

# ADR-052: Immutable, Copy-Not-Reference Composition Snapshot

## Context

Stories 001 and 002 require that a generation result remain explainable and
reproducible even after its source `ImageTemplate` is edited, has its version
bumped, or is archived. A naive design would have the result simply store a
foreign key to the template and re-read its current fields when displaying
history — but that would let a later template edit silently rewrite the
apparent configuration of a historical result, violating the acceptance
criterion that a snapshot "remains unchanged" when its template changes.

## Decision

`CompositionSnapshot` is a separate aggregate that stores a **frozen copy**
of the effective configuration (`model`, `background`, `colors`, `rack`,
`prompt`, `provider`, resolved reference storage keys, and the template
`version` at capture time) as a JSONB value object, not a live reference to
`ImageTemplate`. The repository is insert-only (`save` + read methods, no
`update`), and a database-level unique constraint on
`composition_snapshots.generation_job_id` enforces exactly one snapshot per
generation result — the invariant is guaranteed by the schema, not only by
application code.

## Rationale

Copying the configuration at the moment of capture is the only way to
guarantee historical results are unaffected by future template mutation,
since any live-reference design would need every future template revision to
somehow "not affect" existing historical reads — which is naturally satisfied
by not reading the template at all after capture. Enforcing single-capture
via a DB unique constraint (rather than trusting the service layer to check
"does a snapshot already exist" before inserting) closes a race-condition
window where two concurrent accept-flow calls for the same job could
otherwise both attempt to capture a snapshot.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Frozen copy + DB unique constraint (chosen) | Guarantees historical immutability regardless of template lifecycle; race-safe at the database level | Duplicates configuration data across snapshots (storage cost); requires care to resolve reference keys at capture time | Storage duplication is a small JSONB payload per generation result; correctness guarantee outweighs the cost |
| Live FK to `ImageTemplate` with a `version` column read at display time | No data duplication | Cannot express "unchanged forever" without also snapshotting per-version rows for every field, which is equivalent complexity with worse guarantees since a bug in version pinning would leak live edits into history | Rejected: does not meet the immutability acceptance criterion by construction |
| Versioned template rows (append-only `image_templates` history table) referenced by snapshot | Reuses one versioning mechanism across both templates and snapshots | Couples template edit history to per-generation-result snapshot needs; template edit history and per-result configuration are different concerns (a template revision doesn't always correspond to a captured result) | Rejected: conflates two independent aggregates' lifecycles |

## Consequences

### Positive

- Historical results are guaranteed immutable and reproducible by
  construction, independent of any future template lifecycle changes.
- The database — not application logic alone — prevents duplicate captures
  for the same generation job.
- `regenerate` can safely rebuild a request from the frozen configuration
  without any risk of reading partially-edited template state.

### Negative

- Configuration data is duplicated per snapshot rather than referenced,
  increasing storage slightly (bounded by JSONB size of a template's fields).
- If a template's reference storage key becomes unavailable *before* capture,
  capture must fail explicitly (see domain model invariant 8) rather than
  silently degrading, adding a failure path callers must handle.

### Risks

- **Risk**: Divergence between `ImageTemplate`'s current shape and an older
  snapshot's frozen `effective_configuration` shape if the template schema
  evolves later. **Mitigation**: Treat `effective_configuration` as a
  versioned payload (`template_version` is already stored); any future field
  additions must be optional with safe defaults when reading older snapshots.

## Related

- **Stories**: 002-composition-snapshot
- **Standards**: None to update; this pattern is scoped to this bolt's
  aggregates.
- **Previous ADRs**: ADR-048 (Commit Generation Jobs Before Queue
  Publication) — `regenerate` inherits this guarantee by delegating to the
  existing job-creation path rather than re-implementing it.
