---
bolt: 056-photoshoot-catalog
created: 2026-09-19T01:44:26Z
status: proposed
superseded_by: null
---

# ADR-063: CatalogVersion Is a Hash of the Visible Set

## Context

Story 002 requires `catalog_version` (and the ETag derived from it) to change when an active template or a model of the link owner changes, so BFashion can skip a full download. FR-16 forbids a hand-maintained counter and any new table.

Three derivations were on the table:

1. `max(updated_at)` over visible templates and models — one cheap aggregate query.
2. A persisted counter / version row bumped on every template or model write — extra schema and write-path coupling.
3. A deterministic hash of the *already-filtered* visible set (template ids/versions, model pose photos, plus a schema salt).

`max(updated_at)` is wrong when a row **leaves** the visible set. Archiving a template (045) removes it from this catalog. If the remaining rows keep the same maximum timestamp, BFashion would get a `304` for a catalog that just lost an option. Model pose uploads are also a poor fit: bolt 028 modeled `created_at` on `Model` and `uploaded_at` on `ModelPhoto`, so a new pose is not guaranteed to bump a model-level `updated_at`.

A dedicated version table would work, but this bolt explicitly has no Alembic revision, and every future template/model write would have to remember to bump it.

## Decision

`catalog_version` is `sha256:` plus the first 32 hex chars of SHA-256 over a canonical JSON payload of the **visible** catalog:

- schema salt `photoshoot-options:v1`
- active, in-scope templates: `id`, `version`, `updated_at`, `scope`
- owner models: `id` plus pose photos (`pose`, `photo_id`, `uploaded_at`)
- the closed `cloth_types` list and `max_pose_count`

Arrays are sorted by `id` / `pose`. Presigned URLs and suggestion strings are **not** part of the payload (suggestions are determined by the same templates; URLs are volatile — see ADR-064).

No column, table, or trigger stores this value. It is computed in `PhotoshootCatalogService` after the same reads used to build a `200`.

## Rationale

The hash changes if and only if membership or identity of the visible set changes: archive, revise, new model, new or replaced pose, or a later change to the closed cloth-type set (via the salt / constant list). That is exactly the freshness contract in story 002.

Computing it in-process is cheap relative to the list queries already required. V1 does not add a version-only shortcut query.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Hash of the visible set (chosen) | Correct on add *and* remove; no schema; deterministic | Requires loading the set before `304` | Matches “no new table” and archival correctness |
| `max(updated_at)` only | One aggregate, possibly index-only | Stale after archive/removal; pose uploads may not bump `Model.updated_at` | Would fail story 002 after archival |
| Persisted counter table | `304` without listing rows | Alembic + every write path must bump; easy to forget | Out of unit scope; contradicts “no new storage” |
| Hash including `preview_url` / raw keys | — | Version changes every request; leaks storage keys into the token | Forbidden by NFR-6 and ADR-064 |

## Consequences

### Positive

- Archiving or losing visibility of a template invalidates BFashion’s cache.
- Adding a model or pose does the same without relying on `Model.updated_at`.
- Later cloth-type / shape changes can bump caches by editing the salt or the constant list.

### Negative

- A `304` still pays the list queries; only the body and MinIO signing are skipped (ADR-064).
- Hash definition is now part of the cross-team contract: changing the canonical payload is a cache-bust by design.

### Risks

- **Risk**: An implementer hashes response-order fields (`name`, suggestions, presigned URLs) and versions flap. **Mitigation**: Stage 2 payload is normative; tests lock archive → version change and no-op reread → stable version.

## Related

- **Stories**: 001-photoshoot-options-catalog, 002-catalog-isolation-and-freshness
- **Standards**: Caching — none today; this is the application-level freshness rule for this GET
- **Previous ADRs**: ADR-064 (how the version is shipped as a weak ETag), ADR-060 (whose models/templates enter the set)
