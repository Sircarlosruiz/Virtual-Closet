---
stage: domain-model
bolt: 038-containers
created: 2026-06-18T09:00:00Z
---

## Domain Model: Container Optimization

---

### Context Snapshot

The codebase already has two Dockerfiles:

| File | State |
|------|-------|
| `frontend/Dockerfile` | Multi-stage ✅, non-root ✅, HEALTHCHECK ✅ (hits `/`, not `/api/health`) |
| `backend/Dockerfile` | Single-stage ❌, root user ❌, no HEALTHCHECK ❌, `--reload` in CMD ❌ |

This bolt surgically fixes the backend and strengthens the frontend's health endpoint. It does **not** rewrite what already works.

---

### Entities

#### `ContainerImage`

Represents a built Docker image artifact, scoped to a service and environment target.

| Attribute | Type | Notes |
|-----------|------|-------|
| `service` | `frontend \| backend` | Which application |
| `target_stage` | `dev \| production` | Dockerfile build target |
| `base_image` | string | e.g., `node:22-alpine`, `python:3.13-slim` |
| `estimated_size_mb` | int | Must be < 500MB for frontend, < 300MB for backend |
| `run_as_uid` | int | MUST be >= 1000 (non-root) |
| `health_endpoint` | `HealthEndpoint` | HTTP path probed by Docker + k8s |
| `healthcheck` | `HealthCheckConfig` | Docker HEALTHCHECK instruction parameters |

**Invariant**: `run_as_uid < 1000` → image is invalid for production.
**Invariant**: `--reload` in production CMD → image is invalid.

---

#### `BuildStage`

One named stage within a multi-stage Dockerfile.

| Attribute | Type | Notes |
|-----------|------|-------|
| `name` | string | e.g., `base`, `deps`, `builder`, `runner` |
| `from` | string | Base image or prior stage |
| `purpose` | string | What this stage contributes |
| `produces_artifact` | bool | Whether output is copied to next stage |

**Frontend stages** (already correct):
1. `base` — pnpm enabled on node:22-alpine
2. `deps` — frozen install only (production node_modules)
3. `builder` — `pnpm build` → `.next/standalone`
4. `runner` — minimal runtime with non-root user

**Backend stages** (to be created):
1. `base` — python:3.13-slim + uv installed
2. `deps` — `uv sync --frozen --no-dev` (no dev deps)
3. `runner` — copies only venv + app code; non-root user; production CMD

---

#### `HealthEndpoint`

An HTTP route that responds to readiness/liveness probes from Docker and Kubernetes.

| Attribute | Type | Notes |
|-----------|------|-------|
| `path` | string | e.g., `/api/health` (frontend), `/health` (backend) |
| `method` | `GET` | Always GET |
| `response_status` | int | 200 when healthy |
| `response_body` | JSON | `{"status": "ok"}` minimum |
| `probe_type` | `liveness \| readiness` | k8s distinction (same endpoint, different timeouts) |

**Backend**: `/health` already exists at `main.py:76`. No change needed.

**Frontend**: HEALTHCHECK currently hits `http://localhost:3000/` (root page). Needs a dedicated `/api/health` route returning `{"status":"ok"}` with 200 — avoids coupling probe to UI rendering.

---

#### `HealthCheckConfig`

Docker `HEALTHCHECK` instruction parameters.

| Attribute | Type | Notes |
|-----------|------|-------|
| `test_command` | string | `curl -f` or `wget --spider` |
| `interval` | duration | `30s` — matches k8s default probe period |
| `timeout` | duration | `10s` |
| `start_period` | duration | `30s` frontend, `20s` backend |
| `retries` | int | `3` |

**Tool choice**: `wget` (Alpine has it without curl). Backend slim image needs explicit `curl` install or use `python -c "..."` probe — prefer adding `curl` in deps stage.

---

#### `NonRootUser`

Security boundary enforced by the container runtime.

| Attribute | Type | Notes |
|-----------|------|-------|
| `uid` | int | `1001` (consistent across both images) |
| `gid` | int | `1001` |
| `username` | string | `fastapi` (backend), `nextjs` (frontend — already set) |
| `groupname` | string | `fastapi` (backend), `nodejs` (frontend — already set) |

Frontend already sets `nextjs:nodejs` (uid/gid 1001). Backend needs equivalent.

---

#### `LayerGroup`

A logical grouping of Dockerfile instructions that share cache validity.

| Layer Group | Invalidated when | Strategy |
|-------------|-----------------|----------|
| system deps (apt/curl) | base image changes | early, infrequent |
| python deps (uv sync) | `pyproject.toml` or `uv.lock` changes | copy lockfile → sync → copy code |
| app code | any source change | last; invalidates only final COPY |

Key invariant: **dependency install layer must precede source code COPY**. Reversing this defeats Docker layer caching and forces full reinstall on every code change.

---

### Value Objects

#### `ImageTag`

```
{service}:{env}-{git-sha-7}
```

Examples:
- `virtual-closet/frontend:staging-a1b2c3d`
- `virtual-closet/backend:production-f9e8d7c`

Tag `latest` is banned in production manifests (k8s must always pull a specific digest).

#### `BuildContext`

Set of files sent to Docker daemon for the build. Governed by `.dockerignore`. Files that must be excluded:

**Frontend**: `node_modules/`, `.next/`, `.env*`, `e2e/`, `playwright-report/`
**Backend**: `__pycache__/`, `.venv/`, `*.pyc`, `.env*`, `tests/`, `seed-imgs/`, `alembic/versions/*.py` (migrations run at deploy, not bake)

---

### Domain Rules

1. **No dev dependencies in production images** — `uv sync --no-dev`; no devDependencies in frontend runner stage (standalone already strips them)
2. **Non-root mandatory** — uid/gid 1001 on both images; USER instruction before CMD
3. **Health probe endpoint must be dedicated** — `/api/health` (frontend), `/health` (backend); must not depend on DB connectivity for liveness (only readiness)
4. **No `--reload` in production CMD** — development only; production uses plain `uvicorn` args
5. **Layer order: system → deps → code** — ensures cache hits on code-only changes
6. **HEALTHCHECK start_period ≥ app boot time** — prevents premature restart loops
7. **`.dockerignore` required** — both frontend and backend need one to minimize build context

---

### Relationships

```
ContainerImage
  └── BuildStage[]          (ordered; output of last stage = image)
  └── HealthEndpoint        (HTTP route probed by Docker + k8s)
  └── HealthCheckConfig     (HEALTHCHECK instruction)
  └── NonRootUser           (USER instruction in runner stage)
  └── BuildContext          (files sent to daemon; governed by .dockerignore)
  └── LayerGroup[]          (logical cache groupings within stages)
```

---

### Scope Boundaries

**In scope (this bolt):**
- Fix `backend/Dockerfile` → multi-stage, non-root, HEALTHCHECK, production CMD
- Add `frontend/app/api/health/route.ts` → dedicated health route
- Update frontend HEALTHCHECK to target `/api/health`
- Create `.dockerignore` for both services
- Build documentation (`CONTAINERS.md`)

**Out of scope (later bolts):**
- Container registry push automation → bolt 040 (CI/CD)
- Kubernetes liveness/readiness probe YAML → bolt 039 (k8s-config)
- Trivy security scan CI integration → bolt 040 (CI/CD)
- Celery worker Dockerfile → bolt 039 (k8s-config decides if it's a separate image or same backend image)
