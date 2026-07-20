---
intent: 006-multi-pose-vton-generation
phase: inception
status: context-defined
updated: 2026-07-17T00:00:00Z
---

# Multi-Pose VTON Generation - System Context

## System Overview

Multi-Pose VTON Generation extends the existing Virtual Closet platform. A mayorista groups their own model photos under a new `Model` identity, tagging each photo with a fixed pose type (`front`, `side`, `back`). When submitting a garment for VTON generation against a multi-pose `Model`, the mayorista can deselect specific poses before submitting. The system expands the request into the existing `BatchJob`/`BatchItem` pipeline (one item per selected pose) and registers a new `PoseSet` record linking the batch to the model and garment, so results can be retrieved and displayed as one grouped set of multi-angle outputs.

## Context Diagram

```mermaid
C4Context
    title System Context — 006-multi-pose-vton-generation

    Person(mayorista, "Mayorista", "Wholesale vendor; manages model poses, submits multi-pose generation")

    System(poseUI, "Multi-Pose UI", "New React pages: model+pose management, pose deselection at submission, pose set result view")
    System(modelPoseService, "Model & Pose Domain", "Extends Media Service: new Model aggregate owning 1..N ModelPhoto poses")
    System(poseSetService, "PoseSet Coordination", "New domain extending Batch Job Service: expands pose-aware submissions into BatchJob/BatchItem, registers PoseSet")

    System_Ext(mediaService, "Media Service", "Existing (001): GarmentPhoto storage, legacy ModelPhoto upload/validation")
    System_Ext(batchJobService, "Batch Job Service", "Existing (005): BatchJob/BatchItem creation, atomic submission, status tracking")
    System_Ext(vtonJobService, "VTON Job Service", "Existing (002): individual VTON inference execution via Celery")
    System_Ext(minio, "MinIO", "Existing object storage for photos and results")
    System_Ext(djangoAuth, "Django Auth / JWT", "Existing mayorista authentication")

    Rel(mayorista, poseUI, "Creates models, uploads poses, deselects poses, views pose set results")
    Rel(poseUI, modelPoseService, "REST API: model/pose CRUD", "JSON/HTTPS")
    Rel(poseUI, poseSetService, "REST API: submit poses, view pose set", "JSON/HTTPS")
    Rel(modelPoseService, mediaService, "Reuses file validation + MinIO upload path")
    Rel(poseSetService, batchJobService, "Creates BatchJob + BatchItems (one per selected pose)")
    Rel(batchJobService, vtonJobService, "Delegates per-item job creation (unchanged)")
    Rel(vtonJobService, minio, "Saves result images")
    Rel(modelPoseService, minio, "Stores pose photos")
    Rel(mayorista, djangoAuth, "Authenticates")
```

## External Integrations

- **Media Service** (`001-vton-generation-pipeline`): Reused for file validation (JPG/PNG, 10MB) and MinIO upload conventions; legacy `ModelPhoto` rows are backfilled into implicit single-pose `Model` wrappers here
- **Batch Job Service** (`005-batch-vton-generation`): Reused unchanged — `PoseSet` submissions create standard `BatchJob`/`BatchItem` records; no parallel execution path
- **VTON Job Service** (`002-vton-job-service`): Unchanged; still executes individual inference jobs via Celery/RabbitMQ, one per `BatchItem`
- **MinIO**: Existing storage; pose photos and per-pose results stored under existing mayorista-namespaced conventions
- **Django Auth / JWT**: Existing mayorista authentication; scopes `Model`, poses, and `PoseSet` records per mayorista

## High-Level Constraints

- Must reuse the existing `BatchJob`/`BatchItem` pipeline — no new job-execution or worker infrastructure
- Pose type is a fixed enumeration (`front`, `side`, `back`); no arbitrary pose labels
- `PoseSet` creation must be atomic with `BatchJob`/`BatchItem` creation
- Legacy `ModelPhoto` rows must be backfilled into single-pose `Model` wrappers with zero data loss
- Curated model library is out of scope — multi-pose applies only to mayorista-uploaded models

## Key NFR Goals

- **Performance**: Pose-set submission API < 500ms p95 (enqueue only), matching existing batch submission NFR
- **Reliability**: No orphaned `PoseSet` without a corresponding `BatchJob`; partial pose failures don't block other poses in the set
- **Security**: Mayorista can only view/manage their own `Model`, poses, and `PoseSet` records
- **Observability**: Per-pose status visible in the pose set view in real time, consistent with existing batch item status visibility
