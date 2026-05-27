---
unit: 001-media-service
bolt: 001-media-service
stage: model
status: complete
updated: 2026-05-26T23:05:00Z
---

# Static Model - Media Service

## Bounded Context

**Media Asset Management** — Responsible for all photo assets used in the VTON pipeline: garment photos uploaded by mayoristas, mayorista-owned model photos, and the platform-curated model library. All files are stored in MinIO with metadata in PostgreSQL. This context does NOT handle VTON job processing, only the media assets that jobs reference.

## Domain Entities

| Entity | Properties | Business Rules |
|--------|------------|----------------|
| `GarmentPhoto` | `id` (UUID), `mayorista_id` (UUID), `minio_key` (str), `filename` (str), `content_type` (str), `size_bytes` (int), `uploaded_at` (datetime) | Only JPG/PNG accepted; max 10MB; mayorista can only access their own photos; minio_key format: `garments/{mayorista_id}/{uuid}.{ext}` |
| `ModelPhoto` | `id` (UUID), `mayorista_id` (UUID, nullable), `minio_key` (str), `label` (str), `is_curated` (bool), `content_type` (str), `size_bytes` (int), `uploaded_at` (datetime) | If `is_curated=true` then `mayorista_id=NULL`; curated models are read-only for mayoristas; own uploads use minio_key format `models/{mayorista_id}/{uuid}.{ext}`; curated use `models/curated/{uuid}.{ext}`; same file validation as garment photos |

## Value Objects

| Value Object | Properties | Constraints |
|--------------|------------|-------------|
| `FileType` | `mime_type` (str), `extension` (str) | Only `image/jpeg` (`.jpg`, `.jpeg`) and `image/png` (`.png`) allowed; validated via magic bytes, not extension |
| `FileSize` | `bytes` (int) | Must be ≤ 10,485,760 bytes (10MB); zero-byte files rejected |
| `MinIOKey` | `prefix` (str), `owner_id` (UUID or "curated"), `uuid` (UUID), `extension` (str) | Prefix must be `garments/` or `models/`; owner_id is mayorista UUID for personal uploads or "curated" for library |
| `PresignedURL` | `url` (str), `expires_at` (datetime) | TTL exactly 15 minutes; generated on-demand, never cached permanently |

## Aggregates

| Aggregate Root | Members | Invariants |
|----------------|---------|------------|
| `GarmentPhoto` | Entity only — no child entities | (1) Each GarmentPhoto belongs to exactly one mayorista; (2) minio_key is unique; (3) file type and size validated before persistence |
| `ModelPhoto` | Entity only — no child entities | (1) If curated, mayorista_id is NULL; (2) if not curated, mayorista_id is required; (3) minio_key is unique; (4) curated models cannot be modified via mayorista API |

## Domain Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `GarmentPhotoUploaded` | Successful upload to MinIO and DB persistence | `garment_photo_id`, `mayorista_id`, `minio_key`, `filename`, `size_bytes` |
| `ModelPhotoUploaded` | Successful model photo upload to MinIO and DB persistence | `model_photo_id`, `mayorista_id`, `minio_key`, `label`, `is_curated` |
| `CuratedModelAccessed` | Mayorista requests curated model presigned URL | `model_photo_id`, `mayorista_id`, `presigned_url` |

## Domain Services

| Service | Operations | Dependencies |
|---------|------------|--------------|
| `MediaUploadService` | `upload_garment(mayorista_id, file, content_type) → GarmentPhoto + presigned_url`; `upload_model_photo(mayorista_id, file, content_type, label?) → ModelPhoto + presigned_url` | MinIO client, GarmentPhotoRepo, ModelPhotoRepo, FileTypeValidator, FileSizeValidator |
| `ModelLibraryService` | `list_curated_models() → List[ModelPhoto]`; `list_own_models(mayorista_id) → List[ModelPhoto]`; `get_presigned_url(minio_key) → PresignedURL` | ModelPhotoRepo, MinIO client |

## Repository Interfaces

| Repository | Entity | Methods |
|------------|--------|---------|
| `GarmentPhotoRepo` | `GarmentPhoto` | `create(entity) → GarmentPhoto`; `get_by_id(id, mayorista_id) → GarmentPhoto | None`; `list_by_mayorista(mayorista_id, page, page_size) → List[GarmentPhoto]` |
| `ModelPhotoRepo` | `ModelPhoto` | `create(entity) → ModelPhoto`; `get_by_id(id, mayorista_id) → ModelPhoto | None`; `list_curated() → List[ModelPhoto]`; `list_by_mayorista(mayorista_id, page, page_size) → List[ModelPhoto]` |

## Ubiquitous Language

| Term | Definition |
|------|------------|
| **Mayorista** | Wholesale clothing vendor — the authenticated user who uploads garments and model photos |
| **Garment Photo** | A photo of a clothing item (flat shot or on mannequin) uploaded by a mayorista as VTON input |
| **Model Photo** | A photo of a person (model) used as the target body for VTON generation — either uploaded by mayorista or from curated library |
| **Curated Library** | Read-only collection of pre-approved model photos provided by the platform, available to all mayoristas |
| **MinIO Key** | The object key/path in MinIO storage that uniquely identifies a stored file |
| **Presigned URL** | A short-lived (15 min) S3-compatible URL granting temporary access to a private MinIO object |
| **Namespace** | The mayorista-specific prefix in MinIO (`garments/{mayorista_id}/`, `models/{mayorista_id}/`) ensuring data isolation |
