---
bolt: 055-replicate-execution-reliability
created: 2026-09-19T17:31:00Z
status: proposed
superseded_by: null
---

# ADR-074: Usage Whitelist Is Keyed by Provider, Not Inferred from Payload Keys

## Context

Bolt 044's `UsageAccountingService.normalize` recognizes a fixed set of OpenAI token fields (`total_tokens`, `input_tokens`, `output_tokens`, and their details). Anything else is dropped. Replicate does not emit those fields; it emits prediction identity and metrics (`predict_time`, optionally `total_time`). With the 044 whitelist alone, every Replicate invocation would stay `unknown` **by design** — which is NFR-4's failure mode.

Two other shapes were possible:

1. Infer the vendor from whichever keys appear (`total_tokens` ⇒ OpenAI, `predict_time` ⇒ Replicate).
2. Split into two services.

A mixed or mis-attributed payload (OpenAI job with a stray `predict_time`, Replicate job with a copied `total_tokens`) must not flip `reported` for the wrong provider. Story 005 also requires OpenAI behaviour to stay unchanged and missing fields to stay `unknown`, never `0`.

`GenerationJob.provider` is already persisted and immutable (bolt 052). It is the correct discriminator.

## Decision

**`UsageAccountingService.normalize(provider, model, raw)` selects the whitelist by `provider`. OpenAI and Replicate sets are additive, not substitutes. Keys from the other provider never count toward `reported`.**

- OpenAI whitelist: the 044 token fields, unchanged.
- Replicate whitelist (semantic; concrete aliases confirmed against a real prediction in Stage 4): `prediction_id`, `predict_time`, `total_time` if present. Nested `metrics.predict_time` is flattened; `id` aliases to `prediction_id`.
- `reported` for Replicate ⇔ non-empty `model` **and** at least one of `prediction_id` or `predict_time` with a real value.
- `reported` for OpenAI ⇔ the 044 predicate (recognized token field present). Replicate keys do not satisfy it.
- Absent/`null` fields are omitted. Fabricating `0` is forbidden.
- Unrecognized future keys are dropped; they do not fail normalization.
- Compatible overload: a single-argument `normalize(raw)` is treated as **OpenAI** so intent-008 callers do not silently become Replicate. The worker for Replicate **must** pass `provider` explicitly.
- No monetary `cost` field is derived or exposed on the job GET. If a later billing intent exposes a figure, it is labeled an estimate (out of this ADR's API surface).

`usage_raw` remains JSONB of the **sanitized** subset only (ADR-047). No new columns unless Stage 4 finds a constraint that rejects non-token keys.

## Rationale

The job already knows the vendor. Using that value makes `reported` a statement about **that** provider's telemetry, not about whichever keys happened to be in a dict.

Inferring from keys looks simpler until a mixed payload, a renamed SDK field, or a third provider arrives. Two services would duplicate the `unknown ≠ 0` and sanitization rules that 044 already tests.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Infer vendor from payload keys | No new `provider` argument | Mixed dicts contaminate `reported`; third provider is ambiguous | Breaks the domain invariant |
| Two accounting services | Clear modules | Duplicates unknown-vs-zero and sanitization; worker must still branch | Extra surface, same branch |
| Replace the OpenAI whitelist with a union of all keys | One set | A Replicate job with leftover `total_tokens` would look `reported` for the wrong reason; OpenAI tests would accept Replicate metrics | Story 005 forbids changing OpenAI behaviour |
| Provider-keyed whitelist (selected) | Discriminator already on the job; OpenAI set untouched; Replicate additive | Callers must pass `provider`; one-arg overload defaults to OpenAI | Selected |

## Consequences

### Positive

- Intent 008 token accounting stays a regression suite, not a rewrite.
- A future provider adds a whitelist entry and a `reported` predicate, not a new service.
- Missing Replicate metrics stay `unknown` without writing fake zeros.

### Negative

- The one-argument overload is OpenAI-shaped. A Replicate caller that forgets `provider` will never become `reported` (fail closed for 005, not a silent success).

### Risks

- **Risk**: SDK field names differ from the provisional aliases. **Mitigation**: Stage 4 captures a real prediction and maps aliases; the `reported` predicate (model + identity or `predict_time`) stays.
- **Risk**: Someone later unions the whitelists "to simplify". **Mitigation**: this ADR; tests that OpenAI payloads with only `predict_time` stay `unknown` and Replicate payloads with only `total_tokens` stay `unknown`.

## Related

- **Stories**: 005-replicate-usage-accounting
- **Standards**: `memory-bank/standards/coding-standards.md`
- **Previous ADRs**: ADR-046, ADR-047, ADR-049, ADR-073
