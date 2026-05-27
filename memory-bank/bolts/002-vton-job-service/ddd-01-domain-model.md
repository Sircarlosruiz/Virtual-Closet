---
unit: 002-vton-job-service
bolt: 002-vton-job-service
stage: model
status: complete
updated: 2026-05-26T23:35:00Z
---

# Static Model - VTON Job Service

## Bounded Context

**VTON Job Lifecycle Management** — Responsible for the full lifecycle of a Virtual Try-On generation request: submission, queueing, async processing, status tracking, and result retrieval. This context orchestrates the interaction between the API (synchronous job creation), RabbitMQ/Celery (async task dispatch), the VTONProvider abstraction (AI inference), and MinIO (result storage). It does NOT handle photo uploads (media service) or retry logic (next bolt).

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| `VTONJob` | `id` (UUID), `mayorista_id` (UUID), `garment_photo_id` (UUID), `model_photo_id` (UUID), `cloth_type` (ClothType enum), `status` (JobStatus enum), `retry_count` (int, default 0), `max_retries` (int, from env), `error_reason` (str, nullable), `result_minio_key` (str, nullable), `created_at` (datetime), `started_at` (datetime, nullable), `completed_at` (datetime, nullable) | Status transitions: `queued → processing → completed | failed`; `garment_photo_id` and `model_photo_id` must reference valid photos; `cloth_type` must be valid enum value; mayorista can only access their own jobs; `retry_count` starts at 0 and increments on transient failures |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `ClothType` | `value` (str) | Must be one of: `upper_body`, `lower_body`, `dress`; case-insensitive matching on input |
| `JobStatus` | `value` (str) | Must be one of: `queued`, `processing`, `completed`, `failed`; transitions are unidirectional (no rollback) |
| `JobId` | `value` (UUID) | Unique identifier for a VTON job; generated on submission |
| `ResultMinIOKey` | `prefix` (str), `mayorista_id` (UUID), `job_id` (UUID), `extension` (str) | Format: `results/{mayorista_id}/{job_id}.jpg`; stored in `generated` bucket |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| `VTONJob` | Entity only — no child entities | (1) Each VTONJob belongs to exactly one mayorista; (2) status transitions follow the state machine; (3) `result_minio_key` is only set when `status=completed`; (4) `error_reason` is only set when `status=failed`; (5) `started_at` is set when transitioning to `processing`; (6) `completed_at` is set when transitioning to `completed` or `failed` |

### State Machine

```
queued ──► processing ──► completed
                     │
                     └──► failed
```

- `queued → processing`: When Celery worker picks up the job (idempotency: only if still `queued`)
- `processing → completed`: When VTONProvider succeeds and result stored in MinIO
- `processing → failed`: When VTONProvider fails and no retries remain (retry logic in bolt 003)

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `VTONJobCreated` | Successful job submission | `job_id`, `mayorista_id`, `garment_photo_id`, `model_photo_id`, `cloth_type` |
| `VTONJobProcessing` | Celery worker starts processing | `job_id`, `started_at` |
| `VTONJobCompleted` | Inference succeeds, result stored | `job_id`, `result_minio_key`, `completed_at` |
| `VTONJobFailed` | Inference fails permanently | `job_id`, `error_reason`, `retry_count`, `completed_at` |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| `VTONJobService` | `submit_job(mayorista_id, garment_photo_id, model_photo_id, cloth_type) → { job_id, status }`; `get_job_status(job_id, mayorista_id) → VTONJob DTO`; `validate_photo_ownership(mayorista_id, garment_photo_id, model_photo_id) → bool` | VTONJobRepo, GarmentPhotoRepo, ModelPhotoRepo, Celery app |
| `VTONProvider` (interface) | `generate(garment_url: str, model_url: str, cloth_type: str) → bytes` | — |
| `LocalGPUProvider` (impl) | `generate(...)` — calls local IDM-VTON endpoint | HTTP client |
| `ReplicateProvider` (impl) | `generate(...)` — calls Replicate API | Replicate SDK |

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| `VTONJobRepo` | `VTONJob` | `create(entity) → VTONJob`; `get_by_id_and_mayorista(job_id, mayorista_id) → VTONJob | None`; `get_by_id(job_id) → VTONJob | None`; `update_status(job_id, new_status, **kwargs) → VTONJob`; `list_by_mayorista(mayorista_id, page, page_size) → (list, total)` |
| `GarmentPhotoRepo` | `GarmentPhoto` | `get_by_id_and_mayorista(id, mayorista_id) → GarmentPhoto | None` (from media service) |
| `ModelPhotoRepo` | `ModelPhoto` | `get_by_id(id) → ModelPhoto | None` (curated or own, no ownership filter); `get_by_id_and_mayorista(id, mayorista_id) → ModelPhoto | None` (own only) |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **VTONJob** | A single Virtual Try-On generation request with a full lifecycle from submission to completion or failure |
| **Cloth Type** | The category of garment being processed: `upper_body` (shirts, jackets), `lower_body` (pants, skirts), `dress` (full-body garments) |
| **Job Status** | Current state of a VTONJob in its lifecycle |
| **Queued** | Job has been submitted and is waiting in RabbitMQ for a Celery worker |
| **Processing** | Celery worker has picked up the job and is calling the VTONProvider |
| **Completed** | Inference succeeded and result image is stored in MinIO |
| **Failed** | Inference failed permanently (after all retries exhausted in bolt 003) |
| **VTONProvider** | Abstraction for the AI inference backend — switches between LocalGPU (dev) and Replicate (prod) |
| **Result MinIO Key** | The object key in MinIO where the generated try-on image is stored |
| **Retry Count** | Number of times a failed job has been retried (tracked in PostgreSQL, managed in bolt 003) |
