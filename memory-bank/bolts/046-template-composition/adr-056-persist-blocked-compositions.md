---
bolt: 046-template-composition
created: 2026-09-17T22:34:52Z
status: proposed
superseded_by: null
---

# ADR-056: Persist Fit-Rejected Compositions as Blocked Versions

## Context

Story 003 requires that when an overlay does not fit, "publication is blocked
with a validation error". Two interpretations are possible: (a) reject the
request and persist nothing, or (b) record the rejected attempt as a version
with an explicit `blocked` status and no rendered output. The choice affects
auditability, user experience, and the version sequence.

If nothing is persisted, the staff sees an error but there is no durable record
of *what* was rejected or *why*, and the review UI cannot show the failed
attempt alongside successful ones. If a normal `valid` version were written
with a broken image, the failure would not be distinguishable from success.

## Decision

Fit-rejected compositions are persisted as a `CompositionVersion` with
`status = blocked`, `rendered_key = null`, and the measured `fit_result`
(rendered vs. available dimensions plus a reason). The API returns HTTP `422`
with the structured error `OVERLAY_DOES_NOT_FIT` and includes the blocked
version's `id` in the error context. Blocked versions are never publishable and
are excluded from publication candidacy.

## Rationale

Recording the rejection makes the failure durable and inspectable: the UI can
show "attempt v3 blocked — text 640 px wide, available 512 px", and support can
audit what the staff tried. Because `status` is explicit and `rendered_key` is
null, a blocked version can never be mistaken for a rendered candidate, so this
does not weaken the "only valid versions are publishable" invariant. The
`spec_hash` idempotency rule applies equally to blocked attempts: re-requesting
the same failing spec returns the same blocked record rather than appending
noise.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Persist `blocked` version + 422 (chosen) | Durable reason and dimensions; UI can show the attempt; no ambiguity | Adds rows for failed attempts | Audit value; small storage cost |
| Reject and persist nothing | Simplest; no extra rows | No record of what/why; UI cannot show the failed attempt; support cannot audit | Loses the required validation context |
| Persist a `valid` version with a fallback render | Always produces an image | Violates "exact complete text is rendered"; silently publishes wrong output | Directly violates FR-4 and NFR-3 |
| Auto-shrink font until it fits | Always fits | Changes configured font/size; violates "respects configured font/size" | FR-4 requires the configured style to be respected |

## Consequences

### Positive

- Rejections are auditable with exact dimensions and reason.
- UI and integration can distinguish blocked from valid without ambiguity.
- The version sequence records every composition attempt.

### Negative

- Failed attempts consume version numbers and rows.
- Callers must treat `status = blocked` as non-publishable.

### Risks

- **Risk**: A caller ignores `status` and attempts to publish a blocked
  version. **Mitigation**: `rendered_key` is null for blocked versions, and
  bolt 048's publication path filters on validity; Stage 5 tests assert a
  blocked version cannot become a candidate.

## Related

- **Stories**: 003-deterministic-sku-composition
- **Standards**: None.
- **Previous ADRs**: ADR-054 (Deterministic Spec-Hash Idempotency) — applies to
  blocked attempts as well; ADR-055 (Append-Only Versions).
