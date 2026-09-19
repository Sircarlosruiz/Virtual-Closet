---
bolt: 056-photoshoot-catalog
created: 2026-09-19T01:44:26Z
status: proposed
superseded_by: null
---

# ADR-064: Weak ETag and Deferred Presign on 304

## Context

FR-16 and NFR-1 allow `ETag` / `If-None-Match` / `304` so BFashion can open the staff form often without re-downloading the catalog. The JSON includes `preview_url`, a short-lived MinIO presigned URL regenerated on every successful read (028 media convention, ~15 minutes, never logged).

A **strong** ETag means “this byte representation is identical.” That is false if `preview_url` changes while templates and models do not. Signing URLs up front and then answering `304` would also waste MinIO work that the `304` exists to avoid.

Story 002’s edge case: an `If-None-Match` that matches no known version is ignored and the full `200` is returned. There is no CDN and no Redis cache (unit out of scope).

## Decision

1. Derive the validator from ADR-063’s `catalog_version` (semantic catalog, not the serialized body).
2. Send `ETag: W/"<catalog_version>"` and `Cache-Control: private, no-cache` on `200` and `304`.
3. Compare `If-None-Match` after stripping `W/` and quotes. Any matching token → `304` with **no body** and **no presign calls**. Unknown or absent header → `200` with freshly signed `preview_url`s.
4. `catalog_version` in the JSON equals the token inside the ETag.

`private` keeps shared caches from storing a tenant-specific catalog. `no-cache` forces revalidation on each screen open, which is the intended cadence.

BFashion may reuse a previously downloaded catalog on `304`, but must not assume `preview_url` values from an older `200` are still valid.

## Rationale

Weak ETag is the honest HTTP signal: the catalog *meaning* is unchanged; the bytes (URLs) may differ. Deferring presign until a `200` is confirmed is what makes `304` cheaper than a full reread of the JSON (NFR-1). Database lists still run because V1 has no version index (ADR-063).

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Weak ETag + presign only on `200` (chosen) | Honest HTTP; skips MinIO on hit | Cached preview URLs can expire | Documented for BFashion; TTL is already 15 min |
| Strong ETag over the full JSON | Familiar | Flaps every request because of `preview_url` | Makes `304` useless |
| Omit `preview_url` from V1 | Strong ETag would be honest | FR-16 lists `preview_url` | Out of story scope |
| Sign URLs before the `If-None-Match` check | Simpler control flow | Pays MinIO on every poll | Defeats NFR-1 |
| Shared/CDN cache keyed by ETag | Zero origin on hit | Cross-tenant leak risk; no infra in scope | Unit forbids CDN |

## Consequences

### Positive

- Repeated opens with an unchanged catalog transfer nothing and do not sign URLs.
- Intermediary caches are told not to share the body (`private`).
- The freshness token in the body and the ETag cannot drift.

### Negative

- Clients that treat any ETag as strong may cache expired preview URLs. They must refresh media on `200` or when a URL 403s.
- Implementers must not generate presigns inside the service before the router decides 200 vs 304 — or the service must expose a “version only” path. The Stage 2 flow computes version first, then signs.

### Risks

- **Risk**: Router signs, then returns `304`. **Mitigation**: tests assert zero presign calls on a matching `If-None-Match`.
- **Risk**: Logs print `preview_url`. **Mitigation**: NFR-6 / coding-standards; never log presigned URLs.

## Related

- **Stories**: 002-catalog-isolation-and-freshness
- **Standards**: API conventions have no ETag section yet; add later if more S2S GETs grow validators
- **Previous ADRs**: ADR-063 (what the token hashes), ADR-040 / ADR-061 (auth/visibility still run before any ETag compare)
