---
intent: 001-vton-generation-pipeline
phase: inception
status: complete
created: 2026-05-26T00:00:00.000Z
updated: 2026-05-26T00:00:00.000Z
---

# Requirements: VTON Generation Pipeline

## Intent Overview

End-to-end pipeline for Virtual Try-On (VTON) generation. A mayorista uploads a garment photo (flat or mannequin) and selects a model photo (from their own uploads or a curated library), specifies the cloth type, and submits a generation job. The job is processed asynchronously via Celery/RabbitMQ using IDM-VTON. The mayorista polls for status and retrieves the generated output image when complete. Failed jobs are retried automatically before being marked as failed.

## Business Goals

| Goal | Success Metric | Priority |
|------|----------------|----------|
| Mayoristas can generate AI try-on images | First successful generation within 5 minutes of onboarding | Must |
| Multiple garment types supported | Upper, lower, and dress cloth types all produce correct output | Must |
| Reliable pipeline with retry | < 5% permanent failure rate; transient failures auto-recovered | Must |
| Model photo flexibility | Mayorista can use own model photos or select from curated library | Must |

---

## Functional Requirements

### FR-1: Garment Photo Upload
- **Description**: Mayorista uploads a garment photo (flat product shot or on mannequin). File is stored in MinIO.
- **Acceptance Criteria**: JPG/PNG accepted; max 10MB; file stored in MinIO under mayorista's namespace; upload URL returned.
- **Priority**: Must

### FR-2: Model Photo Management
- **Description**: Mayorista can upload their own model photos OR select from a pre-built curated model library.
- **Acceptance Criteria**: Own uploads stored in MinIO under mayorista's namespace; curated library exposed as read-only list; both sources usable when submitting a job.
- **Priority**: Must

### FR-3: Cloth Type Selection
- **Description**: When submitting a job, mayorista specifies the cloth type to guide the VTON model.
- **Acceptance Criteria**: Supported types: `upper_body`, `lower_body`, `dress`; selection is validated before job creation; invalid type returns 400.
- **Priority**: Must

### FR-4: Job Submission
- **Description**: Mayorista submits a VTON job by providing garment photo, model photo, and cloth type. Job is created and queued.
- **Acceptance Criteria**: `POST /api/vton/generate` returns `{ job_id, status: "queued" }` within 500ms; job record created in PostgreSQL; task published to RabbitMQ.
- **Priority**: Must

### FR-5: Async Processing via Celery
- **Description**: Celery worker picks up the job, calls the configured VTON provider (local GPU or Replicate), and updates job status throughout.
- **Acceptance Criteria**: Job transitions: `queued → processing → completed | failed`; status and timestamps updated at each transition; result image stored in MinIO on completion.
- **Priority**: Must

### FR-6: Job Status Polling
- **Description**: Mayorista polls for job status. When complete, response includes the result image URL.
- **Acceptance Criteria**: `GET /api/vton/jobs/{job_id}` returns current status + `result_url` when completed; returns 404 if job_id unknown; only the job owner can access it.
- **Priority**: Must

### FR-7: Automatic Retry on Failure
- **Description**: If VTON inference fails (provider error, timeout), the job is retried automatically up to a configured max (e.g., 3 attempts) before being marked permanently failed.
- **Acceptance Criteria**: Retry count tracked per job; exponential backoff between retries; after max retries, status set to `failed` with error reason; mayorista sees `failed` status on next poll.
- **Priority**: Must

### FR-8: Job History
- **Description**: Mayorista can list their past VTON jobs with status and results.
- **Acceptance Criteria**: `GET /api/vton/jobs` returns paginated list of jobs for the authenticated mayorista; includes status, cloth_type, created_at, result_url (if complete).
- **Priority**: Should

---

## Non-Functional Requirements

### Performance
| Requirement | Metric | Target |
|-------------|--------|--------|
| Job submission latency | p95 API response | < 500ms |
| Inference time (dev, local GPU) | Job completion | < 60s |
| Inference time (prod, Replicate) | Job completion | < 120s |
| Status poll latency | p95 API response | < 200ms |

### Scalability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Concurrent jobs | Celery worker concurrency | Configurable via env |
| Job queue depth | RabbitMQ queue | No hard limit; Celery manages backpressure |

### Security
| Requirement | Standard | Notes |
|-------------|----------|-------|
| Job ownership | Row-level | Mayorista can only access their own jobs |
| File access | MinIO pre-signed URLs | Short-lived (15 min), not permanent public URLs |
| Auth | JWT HttpOnly cookie | All VTON endpoints require authenticated session |

### Reliability
| Requirement | Metric | Target |
|-------------|--------|--------|
| Permanent failure rate | % of jobs that fail after all retries | < 5% |
| Queue durability | RabbitMQ message persistence | Durable queues, no message loss on restart |

---

## Constraints

### Technical Constraints
- VTON provider is abstracted (`VTONProvider` interface) — implementation switches via `VTON_PROVIDER` env var
- `cloth_type` is a required field on every inference call (IDM-VTON / CatVTON requirement)
- Celery workers must not store state in memory between tasks — all state in PostgreSQL

### Business Constraints
- Replicate API has rate limits in prod — retry logic must respect provider limits
- Generated images are derived from mayorista content — stored under their namespace in MinIO

---

## Assumptions

| Assumption | Risk if Invalid | Mitigation |
|------------|-----------------|------------|
| Mayorista is authenticated before accessing VTON endpoints | Unauthenticated access to paid AI resources | Auth dependency enforced at router level |
| Replicate API is available for prod inference | Production jobs fail entirely | LocalGPU fallback for dev; monitor Replicate uptime |
| IDM-VTON / CatVTON supports all three cloth types | Some cloth types produce poor results | Test each cloth type during Construction spike |

---

## Out of Scope

- Batch generation (multiple garments in one job)
- Webhook / real-time push notifications (polling only for MVP)
- Catalog creation from generated images (separate intent)
- Model photo editing or background removal

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Max retry count and backoff strategy | Carlos | TBD | Pending |
| Curated model library — how many models, who manages them? | Carlos | TBD | Pending |
| Replicate-specific rate limit handling (429 → retry or fail?) | Carlos | TBD | Pending |
