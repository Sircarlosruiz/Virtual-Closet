---
unit: 001-tryoff-model-service
bolt: 015-tryoff-model-service
stage: design
status: complete
updated: 2026-05-31T14:30:00Z
---

# Technical Design - TryOff Health Monitoring

## Architecture Pattern

**Health Monitoring as Cross-Cutting Concern**

Health monitoring is a lightweight cross-cutting concern that sits alongside the inference endpoint. It does not introduce new layers — it reuses the existing FastAPI presentation layer and exposes a single GET endpoint that reads a module-level flag.

```text
┌─────────────────────────────────────────────────┐
│  Presentation (FastAPI)                         │
│  GET /health · POST /tryoff                     │
├─────────────────────────────────────────────────┤
│  Application (HealthService)                    │
│  Read _model_ready flag → return HealthResponse │
├─────────────────────────────────────────────────┤
│  Domain (HealthMonitor)                         │
│  _model_ready lifecycle · HealthState           │
├─────────────────────────────────────────────────┤
│  Infrastructure (Docker, lifespan)              │
│  restart: unless-stopped · healthcheck config   │
└─────────────────────────────────────────────────┘
```

**Rationale**: Health monitoring is intentionally minimal. The `_model_ready` flag is set once at startup and never changes. The GET /health endpoint is a pure read of this flag. No database, no caching, no external dependencies.

---

## Layer Structure

### Presentation Layer
- **GET /health** endpoint returns `JSONResponse` with status code 200 (ready) or 503 (loading)
- No authentication (internal Docker network only)
- Response format: `{"status": "ok"|"loading", "model_loaded": bool, "device": str}`

### Application Layer
- **HealthService.get_health_status()**: Reads `_model_ready` and `_device` from module globals, constructs `HealthResponse`
- No business logic — pure state read

### Domain Layer
- **HealthMonitor**: Owns `_model_ready` flag lifecycle
- Flag set to `True` in `lifespan()` after `pipeline.fuse_lora()` completes
- Flag never reverts to `False` at runtime (container restart required for reload)

### Infrastructure Layer
- **Docker Compose healthcheck**: Periodically calls `curl -f http://localhost:8000/health`
- **Restart policy**: `restart: unless-stopped` ensures container restarts on crash
- **Start period**: 300s grace period for model loading before healthcheck failures count

---

## API Design

### `GET /health` — Container Health Check

**Request**: None (no parameters, no authentication)

**Response**: `application/json`

**Success (model loaded)**:
```json
{
  "status": "ok",
  "model_loaded": true,
  "device": "cuda"
}
```
HTTP 200

**Loading (model not ready)**:
```json
{
  "status": "loading",
  "model_loaded": false,
  "device": "unknown"
}
```
HTTP 503

**Error Responses**:

| Code | Condition | Body |
|------|-----------|------|
| 503 | Model still loading | `{"status": "loading", "model_loaded": false, "device": "unknown"}` |

No other error conditions — endpoint is a pure state read.

---

## Docker Compose Configuration

### Healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 300s
```

**Rationale**:
- **interval: 30s**: Balances responsiveness (detect failure within 30s) with resource usage
- **timeout: 10s**: Generous timeout for health endpoint (should respond in <100ms)
- **retries: 3**: Require 3 consecutive failures before marking unhealthy (avoids false positives)
- **start_period: 300s**: FLUX.2-klein is ~18 GB; model loading takes 2-5 minutes. Ignore healthcheck failures during this window.

### Restart Policy

```yaml
restart: unless-stopped
```

**Rationale**:
- Container restarts automatically on crash (OOM, unhandled exception, SIGKILL)
- Does not restart if explicitly stopped (`docker compose stop`)
- Matches FASHN pattern exactly

---

## Startup Sequence

```text
1. Container starts → uvicorn launches FastAPI app
2. lifespan() enters:
   a. _model_ready = False (initial state)
   b. _load_pipeline() called
      - Downloads weights if not cached
      - Loads FLUX.2-klein-base-9B
      - Loads virtual-tryoff-lora
      - Fuses LoRA: pipeline.fuse_lora(lora_scale=1.0)
   c. _model_ready = True (set after fuse_lora completes)
   d. _device = "cuda"
3. lifespan() yields → server accepts requests
4. GET /health returns 200 with model_loaded: true
5. Docker healthcheck marks container healthy
```

**Failure Handling**:
- If `_load_pipeline()` raises exception → `raise SystemExit(1)` → container exits
- Docker restart policy activates → container restarts within 30s
- Cycle repeats until model loads successfully

---

## Crash Recovery

### OOM Kill (SIGKILL)

```text
1. GPU runs out of memory during inference
2. Linux OOM killer sends SIGKILL to container process
3. Container exits with code 137
4. Docker restart policy activates (restart: unless-stopped)
5. Container restarts within 30s
6. lifespan() runs → model loads → _model_ready = True
7. Docker healthcheck marks container healthy after start_period
```

### Unhandled Exception

```text
1. Unhandled exception in FastAPI app
2. uvicorn catches exception, logs error, continues running
3. Container remains healthy (healthcheck still passes)
4. No restart required
```

### Explicit Stop

```text
1. User runs: docker compose stop tryoff-model
2. Docker sends SIGTERM to container
3. Container exits gracefully
4. Docker restart policy does NOT activate (unless-stopped)
5. Container remains stopped until explicitly started
```

---

## Error Handling

| Error Type | HTTP Code | Response |
|------------|-----------|----------|
| Model not loaded | 503 | `{"status": "loading", "model_loaded": false, "device": "unknown"}` |
| Model loaded | 200 | `{"status": "ok", "model_loaded": true, "device": "cuda"}` |

No other error conditions. Endpoint is a pure state read with no external dependencies.

---

## External Dependencies

| Service | Purpose | Integration |
|---------|---------|-------------|
| Docker Compose | Healthcheck orchestration | YAML configuration |
| Docker Engine | Restart policy enforcement | Container runtime |

---

## Container Lifecycle

### States

```text
[Created] → [Starting] → [Loading Model] → [Ready] → [Running]
                              ↓
                         [Crashed] → [Restarting] → [Loading Model] → ...
```

### Transitions

| From | To | Trigger |
|------|----|---------|
| Created | Starting | `docker compose up` |
| Starting | Loading Model | uvicorn starts, lifespan() begins |
| Loading Model | Ready | `pipeline.fuse_lora()` completes, `_model_ready = True` |
| Ready | Running | Docker healthcheck marks healthy |
| Running | Crashed | OOM kill, unhandled exception, SIGKILL |
| Crashed | Restarting | Docker restart policy activates |
| Restarting | Loading Model | Container restarts, lifespan() runs again |
| Running | Stopped | `docker compose stop` (explicit) |

---

## File Structure

No new files required. Health monitoring is implemented in existing files:

```text
docker/flux/
├── main.py              # GET /health endpoint + _model_ready flag (already implemented in bolt 014)
docker-compose.yml       # healthcheck + restart policy (already configured in bolt 014)
```

---

## Validation Strategy

### Unit Tests (no GPU required)

- Test GET /health returns 503 when `_model_ready = False`
- Test GET /health returns 200 when `_model_ready = True`
- Test response format matches `HealthResponse` schema

### Integration Tests (requires GPU)

- Start container → verify health returns 503 during model loading
- Wait for model to load → verify health returns 200
- Simulate crash (`kill -9`) → verify container restarts within 30s
- Verify Docker healthcheck marks container healthy after restart

### Manual Validation

- `docker compose logs tryoff-model` → verify startup sequence
- `docker inspect tryoff-model` → verify restart policy and healthcheck config
- `curl http://localhost:8003/health` → verify endpoint response
