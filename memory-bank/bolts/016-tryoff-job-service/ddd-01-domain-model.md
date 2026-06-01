---
unit: 002-tryoff-job-service
bolt: 016-tryoff-job-service
stage: model
status: complete
updated: 2026-05-31T15:30:00Z
---

# Static Model - tryoff-job-service

## Bounded Context

**TryOff Job Orchestration**: Manages the lifecycle of garment extraction jobs from submission through async processing to completion. Coordinates between the API layer, Celery task queue, and the FLUX model service.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| TryoffJob | id: uuid, mayorista_id: uuid, source_image_id: uuid, garment_type: GarmentType, status: JobStatus, output_media_id: uuid?, created_at: datetime, completed_at: datetime?, error: string? | Status transitions: pending → processing → complete/failed. Only the owning mayorista can access the job. output_media_id is set only when status=complete. |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| GarmentType | value: string | Must be one of: "upper", "lower", "dress" |
| JobStatus | value: string | Must be one of: "pending", "processing", "complete", "failed" |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| TryoffJob | status, output_media_id, completed_at, error | (1) status can only transition forward: pending → processing → complete/failed. (2) output_media_id is null unless status=complete. (3) completed_at is null unless status is complete or failed. (4) error is null unless status=failed. |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| JobSubmitted | POST /api/tryoff/jobs creates a new job | job_id, mayorista_id, source_image_id, garment_type |
| JobProcessingStarted | Celery worker picks up the job | job_id, started_at |
| JobCompleted | Model service returns output PNG | job_id, output_media_id, completed_at |
| JobFailed | Model service error or final retry exhausted | job_id, error, failed_at |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| TryoffJobService | create_job(mayorista_id, source_image_id, garment_type) → TryoffJob; create_batch(mayorista_id, source_image_id, garment_types[]) → TryoffJob[]; get_job(job_id, mayorista_id) → TryoffJob | TryoffJobRepository, CeleryTaskQueue |
| ModelServiceClient | extract_garment(source_image_url, garment_type) → bytes | httpx, TRYOFF_MODEL_URL env var |

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| TryoffJobRepository | TryoffJob | save(job) → TryoffJob; find_by_id(job_id) → TryoffJob?; find_by_mayorista(mayorista_id, page, page_size) → TryoffJob[]; update_status(job_id, status, output_media_id?, error?) → TryoffJob |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| TryOff Job | A single garment extraction task that processes one source image for one garment type |
| Batch | Multiple jobs submitted together from the same source image (e.g., upper + lower) |
| Source Image | The original photo uploaded by the mayorista (already in media library) |
| Extracted Garment | The output PNG from the FLUX model showing the garment on white background |
| Job Status | Lifecycle state: pending (queued) → processing (Celery running) → complete (success) or failed (error) |
| Model Service | The FLUX container endpoint at TRYOFF_MODEL_URL that performs the actual extraction |
