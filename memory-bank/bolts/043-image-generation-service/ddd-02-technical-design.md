---
bolt: 043-image-generation-service
stage: design
created: 2026-09-17T02:00:00Z
---

# Technical Design: Image Generation Service

## Components

| Layer | Component | Responsibility |
|---|---|---|
| Model | `models/generation_job.py` | SQLAlchemy persistence for the aggregate |
| Repository | `repositories/generation_job_repo.py` | Tenant-safe CRUD and status updates |
| Service | `services/image_generation_service.py` | Request validation and job creation |
| Schema | `api/schemas/image_generation.py` | Pydantic request/response contract |
| Router | `api/routers/image_generation.py` | Staff-only HTTP endpoints |
| Provider | `services/image_generation/providers.py` | Provider protocol and mode capability checks |
| Queue | `tasks/image_generation.py` | Future Celery entry point taking only `job_id` |

## API

`POST /api/image-generation/jobs`

Request fields:

- `mode`: `try_on | text | edit | extraction`
- `provider`: optional; defaults to `openai` except try-on may select `vton`
- `prompt`: required for `text`, `edit`, and `extraction` when provider policy
  requires it
- `garment_id`, `model_id`, `cloth_type`: required for `try_on`
- `reference_image_ids`: required for `edit` and optional additional context

Response: HTTP 202 with `job_id`, `status`, `mode`, `provider`, and timestamp.

`GET /api/image-generation/jobs/{job_id}` returns the same public fields and
never returns provider credentials or raw provider request metadata.

## Persistence

Create `generation_jobs` with UUID primary key, indexed owner/status columns,
JSONB `input_data`, and a check constraint for supported status values. A
foreign key to `mayorista.id` enforces ownership. The JSONB payload is limited
to validated application references; secret filtering is performed before
repository persistence.

## Authorization

The router uses the existing `get_current_mayorista` dependency. The current
account represents the staff boundary in this codebase; no buyer dependency is
accepted by these routes.

## Queue Contract

The API commits the `queued` row and then dispatches a task containing only the
UUID. The worker loads the row, resolves the provider from server settings,
and updates status. This prevents credentials from entering broker messages.

## Failure Handling

- Invalid mode/provider/input: HTTP 422 before persistence.
- Missing OpenAI configuration: job may be marked failed by the worker with a
  safe configuration error; the key itself is never included.
- Queue integration remains injectable so unit tests can assert dispatch
  without RabbitMQ.

## Compatibility

The existing `Generacion` and `VTONProvider` contracts remain unchanged. The
new provider protocol can wrap the existing VTON provider in the implementation
stage rather than changing legacy callers.
