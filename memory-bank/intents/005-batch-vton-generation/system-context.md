---
intent: 005-batch-vton-generation
phase: inception
status: context-defined
updated: 2026-06-04T00:00:00Z
---

# Batch VTON Generation — System Context

## System Overview

The Batch VTON Generation feature extends the existing Virtual Closet platform. A mayorista selects multiple garment+model+cloth_type pairings via a new UI flow and submits them as a named `BatchJob`. The backend creates a `BatchJob` record, enqueues each pairing as a standard `VtonJob` (reusing the existing Celery/RabbitMQ infrastructure), and tracks aggregate progress. Successful job results are automatically saved to the media library tagged with the batch. Failed items are flagged for individual retry.

## Context Diagram

```mermaid
C4Context
    title System Context — 005-batch-vton-generation

    Person(mayorista, "Mayorista", "Wholesale vendor; submits and monitors batch VTON jobs")

    System(batchUI, "Batch VTON UI", "New React pages for batch creation, progress view, and history")
    System(batchService, "Batch Job Service", "New Django domain: BatchJob + BatchItem records, submission API, progress tracking")

    System_Ext(vtonJobService, "VTON Job Service", "Existing: enqueues and executes individual VTON jobs via Celery")
    System_Ext(celeryRabbit, "Celery / RabbitMQ", "Existing async task queue")
    System_Ext(mediaLibrary, "Media Library (MinIO)", "Existing storage; batch results saved here tagged with batch_id")
    System_Ext(django_auth, "Django Auth / JWT", "Existing mayorista authentication")

    Rel(mayorista, batchUI, "Creates batches, views progress, retries failures")
    Rel(batchUI, batchService, "REST API calls", "JSON/HTTPS")
    Rel(batchService, vtonJobService, "Delegates per-item job creation", "Internal Django service call")
    Rel(vtonJobService, celeryRabbit, "Enqueues VTON tasks")
    Rel(vtonJobService, mediaLibrary, "Saves result images")
    Rel(batchService, mediaLibrary, "Tags results with batch_id")
    Rel(mayorista, django_auth, "Authenticates")
```

## External Integrations

- **VTON Job Service** (`001-vton-generation-pipeline`): Reused for per-item job execution; batch service delegates individual job creation
- **Celery / RabbitMQ**: Existing queue infrastructure; no new queues needed
- **Media Library / MinIO**: Existing storage; results tagged with `batch_id` and `batch_name`
- **Django Auth / JWT**: Existing mayorista authentication; scopes batch records per mayorista

## High-Level Constraints

- Must reuse the existing Celery worker pool — no new worker infrastructure
- Batch submission must not block the HTTP response; all job enqueue is async
- Individual `VtonJob` execution logic is unchanged; `BatchJob` is a coordination layer on top
- Hard cap of 100 items per batch enforced at the API boundary

## Key NFR Goals

- **Performance**: Batch submission API < 500ms p95 (enqueue only)
- **Reliability**: 1 failed item has zero blast radius on remaining items
- **Security**: Mayorista can only view/manage their own `BatchJob` records
- **Observability**: Per-item status visible in real time; failures include error message
