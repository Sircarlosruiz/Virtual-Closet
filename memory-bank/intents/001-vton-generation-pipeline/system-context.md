---
intent: 001-vton-generation-pipeline
phase: inception
status: context-defined
updated: 2026-05-26T00:00:00Z
---

# VTON Generation Pipeline - System Context

## System Overview

The VTON Generation Pipeline is the core AI feature of Virtual Closet. It accepts garment photos and model photos, submits inference jobs to IDM-VTON asynchronously via RabbitMQ/Celery, and returns generated try-on images stored in MinIO. The pipeline abstracts the underlying AI provider (local GPU in dev, Replicate in prod) through a common `VTONProvider` interface.

## Context Diagram

```mermaid
C4Context
    title System Context - VTON Generation Pipeline

    Person(mayorista, "Mayorista", "Wholesale clothing vendor. Uploads garments and model photos, submits generation jobs, views results.")

    System(pipeline, "VTON Generation Pipeline", "Manages photo uploads, job lifecycle, and AI inference orchestration.")

    System_Ext(replicate, "Replicate API", "Cloud AI inference provider for IDM-VTON / CatVTON (production).")
    System_Ext(local_gpu, "Local GPU (Dev)", "NVIDIA Titan RTX running IDM-VTON locally (development).")
    System_Ext(minio, "MinIO", "S3-compatible object storage for garment photos, model photos, and generated outputs.")
    System_Ext(rabbitmq, "RabbitMQ", "Message broker for async job dispatch between API and Celery workers.")
    System_Ext(postgres, "PostgreSQL", "Relational store for VTON job records, status, and metadata.")

    Rel(mayorista, pipeline, "Uploads photos, submits jobs, polls status", "REST / HTTPS")
    Rel(pipeline, minio, "Stores and retrieves photos and generated images", "S3 API")
    Rel(pipeline, rabbitmq, "Publishes VTON tasks", "AMQP")
    Rel(pipeline, postgres, "Persists job records and status", "SQL/asyncpg")
    Rel(rabbitmq, pipeline, "Delivers tasks to Celery workers", "AMQP")
    Rel(pipeline, replicate, "Calls inference API (prod)", "REST / HTTPS")
    Rel(pipeline, local_gpu, "Calls inference directly (dev)", "Python / local")
```

## External Integrations

| System | Direction | Data Exchanged | Protocol | Risk |
|--------|-----------|----------------|----------|------|
| **MinIO** | Outbound (write) + Inbound (read) | Garment photos, model photos, generated images | S3 API | Low |
| **RabbitMQ** | Outbound (publish) + Inbound (consume) | VTON task messages | AMQP | Medium |
| **PostgreSQL** | Outbound (read/write) | Job records, status, metadata | SQL async | Low |
| **Replicate API** | Outbound (prod) | Garment URL, model URL, cloth_type → generated image URL | REST | High |
| **Local GPU** | Outbound (dev) | Same as Replicate | Python in-process | Low |

## High-Level Constraints

- The `VTONProvider` interface must be used for all inference calls — no direct Replicate SDK calls outside the provider
- `cloth_type` is mandatory on every inference call (`upper_body`, `lower_body`, `dress`)
- Celery workers are stateless — all state in PostgreSQL; no in-memory job state
- All file access to mayoristas is through short-lived MinIO pre-signed URLs (15 min TTL), never permanent public URLs
- Authentication is a pre-condition — all endpoints require a valid JWT session (mayorista must already exist)

## Key NFR Goals

- Job submission API response < 500ms (async — worker handles the heavy work)
- Inference completion < 60s (local dev), < 120s (Replicate prod)
- Permanent failure rate < 5% after retries
- Job ownership enforced at row level — mayoristas can only access their own jobs
