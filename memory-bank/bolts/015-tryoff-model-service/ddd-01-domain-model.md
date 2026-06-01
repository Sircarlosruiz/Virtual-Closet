---
unit: 001-tryoff-model-service
bolt: 015-tryoff-model-service
stage: model
status: complete
updated: 2026-05-31T14:15:00Z
---

# Static Model - TryOff Health Monitoring

## Bounded Context

**Health Monitoring**: A cross-cutting concern within the TryOff Inference bounded context. This subdomain manages the container's health state, exposes readiness to external systems (job service, Docker Compose), and ensures automatic recovery from failures.

**Context Map**:
- **Upstream**: ModelPipeline (provides `_model_ready` signal)
- **Downstream**: `002-tryoff-job-service` (queries GET /health before routing jobs), Docker Compose (healthcheck)
- **Relationship**: Supplier to job service; monitored by Docker orchestrator

---

## Domain Entities

- **HealthStatus**: `state: str, model_loaded: bool, device: str` - Represents the current health state of the container. Immutable snapshot returned by GET /health. State values: `"loading"`, `"ok"`.

---

## Value Objects

- **HealthState**: `value: str` - Enum-like value object. Allowed values: `"loading"`, `"ok"`. Equality by value. Transitions: `loading → ok` (one-way, at startup).
- **ModelReadyFlag**: `ready: bool` - Module-level boolean tracking whether the FLUX pipeline has completed loading and LoRA fusion. Transitions: `False → True` exactly once at startup. Never reverts to `False` at runtime.
- **HealthResponse**: `status: str, model_loaded: bool, device: str` - JSON response structure for GET /health. Immutable per request.
- **RestartPolicy**: `policy: str` - Docker restart policy value. Fixed: `"unless-stopped"`. Ensures container restarts on crash unless explicitly stopped.

---

## Aggregates

- **HealthMonitor** (Root): Members: `_model_ready: bool`, `_device: str`, `_health_state: HealthState` - Invariants: (1) `_model_ready` transitions from `False → True` exactly once when `pipeline.fuse_lora()` completes. (2) `_health_state` is derived from `_model_ready` (loading if False, ok if True). (3) GET /health returns 503 when `_model_ready` is False, 200 when True. (4) Container restart policy is `unless-stopped` (Docker-level, not application-level).

---

## Domain Events

- **ModelReady**: Trigger: `pipeline.fuse_lora()` completes successfully - Payload: `{timestamp, device, vram_used_mb}`. Sets `_model_ready = True`.
- **HealthCheckRequested**: Trigger: GET /health endpoint called - Payload: `{timestamp, model_ready, status_code}`. Logged for observability.
- **ContainerRestarted**: Trigger: Docker restart policy activates after crash - Payload: `{timestamp, exit_code, restart_count}`. Logged by Docker, not application.

---

## Domain Services

- **HealthService**: Operations: `get_health_status() -> HealthResponse` - Dependencies: `_model_ready` flag, `_device` string. Returns current health state with appropriate HTTP status code (200 or 503).

---

## Repository Interfaces

- **None**: Health state is ephemeral (in-memory flag). No persistence required.

---

## Ubiquitous Language

- **Health Check**: GET /health endpoint that returns container readiness status
- **Model Ready**: State indicating the FLUX pipeline has finished loading and is accepting inference requests
- **Loading State**: Transient state during startup when model weights are being loaded and LoRA is being fused
- **Restart Policy**: Docker-level configuration (`unless-stopped`) that ensures container restarts after crash
- **Healthcheck**: Docker Compose healthcheck that periodically calls GET /health to mark container as healthy/unhealthy
- **Start Period**: Grace period (300s) during which Docker healthcheck failures are ignored (allows time for model loading)
- **Liveness**: Container is running (Docker-level)
- **Readiness**: Container is ready to serve requests (application-level, model loaded)
