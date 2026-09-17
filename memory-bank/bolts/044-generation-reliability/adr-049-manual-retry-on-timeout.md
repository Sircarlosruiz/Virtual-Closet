---
bolt: 044-generation-reliability
created: 2026-09-17T17:10:00Z
status: proposed
superseded_by: null
---

# ADR-049: Timeout Is an Unresolved Outcome Requiring Manual Retry

## Context

When a provider call times out, the platform does not know whether OpenAI
actually completed the generation (and possibly billed for it) or never
processed the request. Automatically retrying on timeout — the same way a
`429` is retried — risks issuing a duplicate paid provider call for work
that may have already succeeded, silently doubling cost and potentially
producing two results for one job.

## Decision

Classify a worker-side timeout as its own outcome, `timed_out`, distinct
from `failed` (terminal) and `429` (transient/auto-retryable). A
`timed_out` invocation records `usage_status = unknown` and does **not**
trigger an automatic Celery retry. The job surfaces this ambiguous state to
staff, who must explicitly call `POST .../{job_id}/retry` to start a new
attempt after confirming a duplicate is acceptable or unlikely.

## Rationale

Automation is safe only when the outcome is known. `429` responses are
unambiguous (the provider is telling us to back off; no work was done), so
they are safe to auto-retry. A timeout is a "did it happen or not" gap that
only a human reviewing the specific case can resolve responsibly.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Auto-retry timeouts like 429 (up to the same cap) | Simple, one retry code path | Risks duplicate paid provider calls and duplicate results | Cost/duplication risk unacceptable |
| Never allow retry on timeout, force a new job | Avoids any ambiguity about which attempt "owns" the result | Loses attempt history continuity; forces staff to resubmit full inputs | Worse UX for no added safety over a scoped manual retry |
| Manual, staff-initiated retry on the same job (selected) | Keeps attempt history intact; defers the duplicate-risk judgment call to a human who can check for a result first | Adds one endpoint and a staff action step | Selected |

## Consequences

### Positive

- No automatic duplicate provider spend from ambiguous timeouts.
- Attempt history clearly distinguishes "we know it failed" from "we don't
  know what happened."

### Negative

- Staff must take an explicit action to recover from a timeout; there is no
  self-healing path for this specific failure mode.

### Risks

- Staff could retry without checking for a possibly-completed duplicate
  result. Mitigation: the retry endpoint and job detail view surface prior
  attempt history so staff can see if a result already exists before
  retrying.

## Related

- **Stories**: 004-retry-idempotency-limits
- **Standards**: `memory-bank/standards/system-architecture.md`
- **Previous ADRs**: ADR-048
