---
id: 003-container-health-monitoring
unit: 001-tryoff-model-service
intent: 004-tryoff-garment-extraction
status: draft
priority: must
created: 2026-05-31T00:00:00Z
assigned_bolt: 015-tryoff-model-service
implemented: false
---

# Story: 003-container-health-monitoring

## User Story

**As a** platform engineer
**I want** the TryOff container to expose a health endpoint and auto-restart on failure
**So that** the job service can detect model readiness and the system recovers automatically

## Acceptance Criteria

- [ ] **Given** the model is fully loaded, **When** GET /health is called, **Then** it returns `{"status": "ok", "model_loaded": true}` with HTTP 200
- [ ] **Given** the model is still loading, **When** GET /health is called, **Then** it returns `{"status": "loading", "model_loaded": false}` with HTTP 503
- [ ] **Given** the container crashes (any reason), **When** Docker detects the exit, **Then** the container automatically restarts and reloads the model (restart policy: `unless-stopped`)
- [ ] **Given** the container is healthy, **When** the job service queries GET /health before submitting a job, **Then** it correctly routes the job only if `model_loaded: true`

## Technical Notes

- Endpoint: `GET /health` — no authentication required (internal network)
- Track a module-level `_model_ready: bool` flag set to `True` after `pipeline.fuse_lora()` completes
- Docker Compose healthcheck: `test: ["CMD", "curl", "-f", "http://localhost:8003/health"]`, interval 30s, retries 3
- Container management commands follow FASHN pattern (same `Makefile` / `docker` CLI helpers)
- Port mapping: internal 8003 (or configurable via env var `TRYOFF_MODEL_PORT`)

## Dependencies

### Requires
- 001-flux-container-setup
- 002-tryoff-inference-api (container must be functional to validate health)

### Enables
- 002-tryoff-job-service (job service checks health before routing jobs)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Container OOM kill (SIGKILL) | Docker restart policy kicks in; container restarts within 30s |
| Health check endpoint called before model finishes loading | Returns 503 with `model_loaded: false` |
| Network partition between job service and model container | Job service gets connection refused; Celery retries job |

## Out of Scope

- Prometheus/Grafana metrics (future observability work)
- GPU utilization reporting
- Multi-replica health aggregation
