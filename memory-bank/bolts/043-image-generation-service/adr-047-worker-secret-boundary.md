---
bolt: 043-image-generation-service
created: 2026-09-17T04:07:47Z
status: proposed
---

# ADR-047: Resolve Provider Secrets Only Inside Workers

## Context

OpenAI credentials are platform secrets. Browser requests, API responses,
database payloads, logs, and broker messages must not contain the API key.
Workers need enough information to execute a job asynchronously.

## Decision

Persist only sanitized application-owned inputs and send only the durable
`job_id` through Celery. The worker reloads the job and resolves the provider
credential from server-side settings at execution time.

## Rationale

The job ID is sufficient to reload the complete validated contract and keeps
secrets out of every transport boundary. Server-side settings provide one
controlled credential source.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| Include the API key in the job payload | Simple worker invocation | Leaks through broker inspection, retries, and logs | Security unacceptable |
| Store credentials in `input_data` | Easy to associate with a job | Persists secrets in the database and backups | Security unacceptable |
| Send only `job_id` and resolve in worker | Minimal broker data and centralized secret access | Worker must access configuration | Selected |

## Consequences

### Positive

- Client and broker contracts contain no credentials.
- Secret rotation applies to future worker executions without rewriting jobs.

### Negative

- Workers require correctly configured server-side environment settings.
- A missing credential is discovered at execution time.

### Risks

- Accidental logging of provider configuration remains possible. Keep secret
  values out of exception messages and structured logs.

## Related

- **Stories**: 001-staff-provider-selection, 002-staff-generation-jobs
- **Standards**: `memory-bank/standards/coding-standards.md`
- **Previous ADRs**: ADR-005
