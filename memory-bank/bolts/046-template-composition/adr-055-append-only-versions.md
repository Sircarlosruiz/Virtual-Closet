---
bolt: 046-template-composition
created: 2026-09-17T22:34:52Z
status: proposed
superseded_by: null
---

# ADR-055: Append-Only Composition Versions With Explicit Re-Selection

## Context

FR-4 and FR-12 require that changing only the SKU or its style creates a **new
version** without replacing the published image, and that publishing a new
version requires an explicit staff selection. A naive design would let a
`CompositionVersion` row be updated in place (version number bumped, output
overwritten), which would silently replace whatever the gallery was serving and
break the audit trail of what was actually published.

This mirrors, for composed output, the immutability problem ADR-052 solved for
the input configuration snapshot.

## Decision

`composition_versions` is **append-only**: the repository exposes `append` and
read methods only — no `update` and no `delete`. Every change to SKU text,
placement, or style appends a new `CompositionVersion` with
`version = max(version) + 1` computed under a row lock on the parent overlay.
Publication/selection state is **not** stored here; bolt 048 owns it, and it
must require a fresh explicit selection whenever the latest valid version
changes.

## Rationale

Append-only versions make "what was published" permanently reconstructible:
each composed output is an addressable, immutable row, so a later recompose can
never rewrite history. Keeping selection state out of this aggregate preserves
the boundary between composition (this bolt) and publication (bolt 048), so the
same `CompositionVersion` can be considered by multiple publication flows
without this table encoding their state.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Append-only versions (chosen) | Full history; published output can never be silently replaced; simple audit | More rows over time; caller must resolve "latest" | Storage is small per version; correctness is required by FR-4/FR-12 |
| Mutable row with a version counter | Fewer rows; simple "current" read | Overwrites prior output; destroys audit trail; contradict FR-4 "without replacing the published" | Directly violates the acceptance criterion |
| Append-only versions + `is_published` flag on the row | Single read for published output | Couples composition to publication state; publication is bolt 048's bounded context | Cross-context coupling and duplicated state |

## Consequences

### Positive

- Prior published images and their exact bytes remain forever reconstructible.
- A SKU/style change is a pure append; no in-place mutation risk.
- Selection state stays entirely in bolt 048's bounded context.

### Negative

- The version table grows monotonically; reads must select the latest valid
  version (indexed by `(overlay_id, version)`).
- Callers must not assume the highest version is published — only staff
  selection (bolt 048) determines publication.

### Risks

- **Risk**: A caller treats "latest valid version" as "published".
  **Mitigation**: The API contract exposes `status` and version identity only;
  no publication flag is returned. Bolt 048 enforces the re-selection rule, and
  Stage 5 tests assert that recompose never alters a previously referenced
  version.

## Related

- **Stories**: 003-deterministic-sku-composition, 002-publication-selection
  (bolt 048)
- **Standards**: None.
- **Previous ADRs**: ADR-052 (Immutable, Copy-Not-Reference Composition
  Snapshot) — same immutability principle applied to composed output.
