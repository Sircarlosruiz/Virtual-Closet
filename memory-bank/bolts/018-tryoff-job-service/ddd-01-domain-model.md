---
stage: model
bolt: 018-tryoff-job-service
created: 2026-05-31T20:05:00Z
---

## Static Model: 018-tryoff-job-service

### Entities

- **TryoffJob**: id, mayorista_id, source_image_id, garment_type, status, retry_count, max_retries, error_reason, output_minio_key, created_at, started_at, completed_at - Already modeled in bolt 016

### Aggregates

- **TryoffJob Aggregate**: Root: TryoffJob - Members: SourceImage - Invariants: mayorista_id must match, status transitions valid

### Domain Services

- **TryoffJobService**: Operations: list_jobs(mayorista_id, page, page_size) - Dependencies: TryoffJobRepo, MinIOClient

### Repository Interfaces

- **TryoffJobRepo**: Entity: TryoffJob - Methods: list_by_mayorista(mayorista_id, page, page_size) → (list[TryoffJob], int)

### Ubiquitous Language

- **Job History**: Paginated list of past TryOff extraction jobs for a mayorista
- **Pagination**: page/page_size parameters with total count for navigation
