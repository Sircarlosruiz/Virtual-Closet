---
bolt: 046-template-composition
created: 2026-09-17T22:34:52Z
status: proposed
superseded_by: null
---

# ADR-053: Synchronous In-Request Composition Over Queued Execution

## Context

`system-context.md` lists RabbitMQ/Celery as the mechanism for "inferencia,
composición y publicación". The deterministic SKU compositor introduced by
bolt 046 is a different kind of workload than inference: it is a purely local,
CPU-bound rendering step with no network dependency, and it must return a fit
validation result (FR-4) to the staff immediately so an invalid SKU/placement
can be corrected before publication.

Queuing composition would require a second asynchronous state machine
(pending/composing/failed) analogous to `GenerationJob`, plus polling or
webhooks for the fit outcome — duplicating infrastructure already justified
only by the *network-bound* inference workload.

## Decision

Run composition **synchronously inside the HTTP request** for V1. The render
function is isolated behind `SkuCompositionService` with a tight interface
(`compose(base_image, spec) → CompositionVersion`), so it can be relocated to
a Celery task later without changing the API, the domain model, or the
persistence layer.

## Rationale

A synchronous call best satisfies the immediate-feedback requirement of FR-4
while keeping the V1 system free of a redundant job lifecycle. The system
context's Celery entry for "composición" remains satisfied in spirit — the
composition *work* is still orchestrated by the backend; only its transport
differs. If a future requirement introduces large canvases, batch
recomposition across many results, or heavy fonts, the service seam allows a
clean migration.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Synchronous in-request (chosen) | Immediate fit feedback; no new job state machine; simplest call path | Request time bounded by render time; no automatic retry of a failed render | Render is local and sub-second for V1 sizes; fit failures are user-correctable, not transient |
| Celery task with polling | Consistent with inference transport; decouples long renders | New job/result lifecycle; staff must poll for fit errors; more moving parts | Fit validation is a user-input error, not an async workload; queuing adds latency and complexity without benefit |
| Precompute on accept, before request | No visible latency | Spec not yet known at accept time; would need re-queue on every SKU edit | Spec is chosen/edited by staff after the result exists |

## Consequences

### Positive

- Fit validation errors surface immediately (FR-4, story criterion 3).
- No second async state machine or queue consumer to build and operate.
- Composition is trivially testable — the renderer is a pure function.

### Negative

- A very large base image or expensive font could push request latency up.
- A server crash mid-render loses the attempt (no persisted retry); the next
  request re-runs it deterministically.
- The service is a synchronous dependency on the object-storage read of the
  base image.

### Risks

- **Risk**: Image sizes grow beyond the synchronous latency budget.
  **Mitigation**: The service seam (`SkuCompositionService`) allows moving the
  render to Celery without API/model changes; add a latency metric in Stage 4
  and revisit if p95 exceeds the budget.

## Related

- **Stories**: 003-deterministic-sku-composition
- **Standards**: Consider noting the "local deterministic steps may run
  synchronously" guideline in `system-architecture.md` if more such steps
  appear.
- **Previous ADRs**: ADR-048 (Commit Generation Jobs Before Queue Publication)
  — that pattern remains required for inference, not for composition.
