---
bolt: 043-image-generation-service
stage: model
created: 2026-09-17T02:00:00Z
---

# Domain Model: Image Generation Service

## Aggregate

`GenerationJob` is the aggregate root. A job is owned by the submitting staff
account and contains the immutable request contract needed to execute one
generation. V1 produces at most one result per job.

## Entities

### GenerationJob

| Field | Meaning |
|---|---|
| `id` | Durable UUID returned to the caller |
| `owner_id` | Staff account that submitted the job |
| `mode` | `try_on`, `text`, `edit`, or `extraction` |
| `provider` | `openai` or the configured VTON provider |
| `status` | `queued`, `processing`, `completed`, or `failed` |
| `input_data` | Sanitized media references and mode-specific inputs |
| `created_at`, `updated_at` | Lifecycle timestamps |
| `result_key` | Optional private object-storage key |
| `error_code` | Safe, non-secret failure classification |

The provider credential is not part of the aggregate and is never accepted in
the API request or persisted in `input_data`.

## Value Objects

- `GenerationMode`: finite set of supported modes.
- `GenerationProvider`: `openai` for all non-try-on modes, or `openai` / `vton`
  for try-on.
- `GenerationInput`: mode-specific validated payload. References are storage
  keys or application-owned media IDs, never credentials or arbitrary URLs.

## Invariants

1. Only authenticated staff may create a job.
2. `text` requires a non-empty prompt.
3. `edit` requires a prompt and at least one reference image.
4. `extraction` requires a source image.
5. `try_on` requires garment, model, and cloth type; only `openai` and `vton`
   providers are valid.
6. `text`, `edit`, and `extraction` only accept `openai`.
7. OpenAI credentials are resolved inside the worker/provider adapter.
8. A newly persisted job is always `queued`; enqueueing is performed after the
   transaction boundary and failures must not expose a secret.

## State Transitions

```text
queued -> processing -> completed
                    \-> failed
```

The reliability bolt owns retries, idempotency, invocation history, limits,
and usage accounting. This bolt only establishes the durable job contract and
provider/mode validation.

## Boundaries

- `GenerationJobRepository` owns persistence.
- `GenerationJobService` owns validation and creation.
- `ImageGenerationProvider` owns provider-specific execution.
- API schemas expose identifiers, status, mode, and provider only.
- Celery integration receives a job ID, then reloads the aggregate.
