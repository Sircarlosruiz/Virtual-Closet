---
bolt: 055-replicate-execution-reliability
created: 2026-09-19T17:31:00Z
status: proposed
superseded_by: null
---

# ADR-073: Usage Telemetry Lives on the Adapter Sidecar, Not on `generate`'s Return Type

## Context

Story 005 requires `UsageAccountingService` to persist Replicate telemetry (`prediction` identity, `predict_time` / metrics, identified model) so a real invocation can become `usage_status: reported`. Today `UsageAccountingService` only sees what the worker passes it after `ImageGenerationProvider.generate`.

ADR-046 defines that protocol: adapters return the generated image. Bolt 043's OpenAI adapter and bolt 052's `ReplicateTryOnAdapter` (a wrap of `CatVTONReplicateProvider`) share that return type. Changing `generate` to return `(image, usage)` — or a result DTO — would ripple through OpenAI, every 043/052 test of the contract, and any future adapter.

The worker still needs a place to read unsanitized-but-bounded telemetry **after** the call and **before** `normalize(provider, model, raw)`, without a second HTTP client "just for metrics" and without editing `catvton_replicate_provider.py` unless Stage 4 proves the wrap cannot see the prediction object.

## Decision

**Keep ADR-046's `generate` return type as the image. Capture Replicate usage on the adapter instance as a sidecar (`last_usage`, `last_model`) written during the same `generate` call. The worker reads the sidecar, then calls `UsageAccountingService.normalize`.**

- `last_usage` is the raw-but-bounded dict (prediction id, metrics) **before** whitelist sanitization. `UsageAccountingService` is still the only writer of `usage_raw`.
- `last_model` is the identified model string; if missing, `reported` cannot fire.
- OpenAI does not require the sidecar: the worker keeps passing the token dict it already has. The sidecar is optional there.
- On timeout, there is no reliable sidecar → `normalize(..., raw=None)` → `unknown` (ADR-049).
- Forbidden: a second Replicate client for metrics; parsing logs; putting credentials, image bytes, or prompts on the sidecar.

If Stage 4 cannot obtain `prediction.id` / `metrics` from the wrap, the **smallest** hook that exposes that object on the existing provider is allowed. A new HTTP client is not. That hook does not change this ADR's return-type decision.

## Rationale

Telemetry is a property of **one invocation on one adapter instance**, not a second output of the generation protocol. Widening `generate` would treat usage as part of the image contract and force every adapter — including those with no usage — to change.

A sidecar keeps 052's wrap-not-rewrite rule: `CatVTONReplicateProvider` stays the HTTP owner; the try-on adapter is the place that already translates `input_data` and can copy prediction fields it already observed.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Change `generate` → `(bytes, usage)` / result DTO | Explicit; no instance state | Breaks ADR-046, OpenAI adapter, 043/052 contract tests | Ripple larger than the telemetry need |
| Sidecar on the adapter (selected) | Protocol intact; scoped to Replicate; worker already owns `normalize` | Instance state must not leak across jobs; tests must reset/read after each call | Selected |
| Edit `catvton_replicate_provider.py` to return metrics | Source of truth at the HTTP call | Contradicts 052 "wrap, don't edit"; couples VTON callers to usage | Only a last-resort hook if the wrap is blind |
| Second Replicate client for `predictions.get` | Clean metrics API | Extra billed/rate-limited call; two clients | Forbidden by unit brief and this bolt |
| Infer usage later from Replicate dashboard / logs | No code in the adapter | Not durable on `provider_invocations`; NFR-4 fails | Not an implementation |

## Consequences

### Positive

- OpenAI and the ADR-046 protocol stay unchanged.
- `UsageAccountingService` remains the sanitizer; the adapter does not write Postgres.
- 052's wrap of `CatVTONReplicateProvider` stays the integration point.

### Negative

- Callers must read the sidecar immediately after `generate` on the same instance. A reused adapter without reset could report the previous job's usage.
- Instance state is less visible than a return value; tests must assert the sidecar explicitly.

### Risks

- **Risk**: The wrapped provider returns only bytes/URL and hides the prediction. **Mitigation**: Stage 4 must capture a real prediction; if the wrap cannot see id/`predict_time`, add the smallest hook on the existing provider. Do not invent a second client. `reported` is a bolt-close criterion, not optional.

- **Risk**: Sidecar includes secrets or image bytes. **Mitigation**: Whitelist happens in `UsageAccountingService`; adapter copies only identity + metrics + model; tests assert absence of API keys.

## Related

- **Stories**: 005-replicate-usage-accounting
- **Standards**: `memory-bank/standards/tech-stack.md` (Replicate as prod provider)
- **Previous ADRs**: ADR-046, ADR-047, ADR-049, ADR-065
