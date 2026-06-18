---
stage: technical-design
bolt: 038-containers
created: 2026-06-18T09:30:00Z
---

## Technical Design: Container Optimization

---

### Summary of Changes

| File | Action | Why |
|------|--------|-----|
| `backend/Dockerfile` | Full rewrite | Single-stage → multi-stage; add non-root user, HEALTHCHECK, production CMD |
| `frontend/Dockerfile` | Patch 1 line | HEALTHCHECK target `/` → `/api/health`; extend start_period |
| `frontend/app/api/health/route.ts` | Create | Dedicated health route for k8s probes |
| `backend/.dockerignore` | Create | Exclude tests, ML seed images, venv, .env from build context |
| `frontend/.dockerignore` | Already exists | Add `.env*` exclusion (currently missing) |
| `backend/pyproject.toml` | Move test deps to `[dev]` | Exclude pytest from production image |
| `CONTAINERS.md` | Create | Build/run documentation |

---

### 1. Backend `pyproject.toml` — Move Test Deps to Dev Group

**Problem**: `pytest` and `pytest-asyncio` are in main `[dependencies]`, so `uv sync --frozen --no-dev` still includes them in the production image.

**Fix**: Move to `[dependency-groups]` dev group:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
]
```

Remove from `dependencies[]`. Run `uv lock` to regenerate lockfile. This is the only pyproject.toml change.

---

### 2. Backend Dockerfile — Full Rewrite

**Design**: 3-stage build (base → deps → runner).

```
base    python:3.13-slim + uv + curl (tools needed in all stages)
  │
deps    copy lockfiles → uv sync --frozen --no-dev → .venv populated
  │
runner  copy .venv + app code; create non-root user; HEALTHCHECK; production CMD
```

**Why `curl` in base?** The HEALTHCHECK in runner needs a way to probe `localhost:8000/health`. `python:3.13-slim` has no wget. Adding `curl` is ~3MB; Python-based probe adds ~0.5s startup overhead per check.

**Why not 2 stages?** The `deps` intermediate stage exists so the `.venv` install layer (the heaviest and slowest) only invalidates when `pyproject.toml` or `uv.lock` changes — not on every code edit.

**Final Dockerfile**:

```dockerfile
FROM python:3.13-slim AS base
RUN pip install --no-cache-dir uv && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

FROM base AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 fastapi && \
    adduser --system --uid 1001 --gid 1001 --no-create-home fastapi

COPY --from=deps /app/.venv /app/.venv
COPY --chown=fastapi:fastapi . .

ENV PATH="/app/.venv/bin:$PATH"

USER fastapi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Layer invalidation map**:

| Change | Layers rebuilt |
|--------|---------------|
| App code only | `COPY --chown=fastapi . .` onward |
| `pyproject.toml` / `uv.lock` | `uv sync` + all layers after |
| Base image update | Everything |

**Image size expectation**: `rembg[cpu]` (onnxruntime, numpy) + `opencv-python-headless` are runtime dependencies totalling ~400–600MB. The production image will be ~600–800MB. This is a known constraint of the current dependency structure. Extracting ML deps to an optional uv group is deferred to a future optimization bolt.

**Production CMD note**: `docker-compose.yml` overrides CMD with `sh -c "uv run alembic upgrade head && uv run uvicorn ... --reload"` for dev. The Dockerfile CMD is the production default — no `--reload`, no alembic (handled by k8s Job per ADR-030).

---

### 3. Frontend Dockerfile — Minimal Patch

The existing frontend Dockerfile is correct. Two targeted changes:

**Change 1** — HEALTHCHECK target + start_period:
```dockerfile
# BEFORE
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# AFTER
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1
```

`start_period` raised from 10s → 30s: Next.js standalone cold-start in a container takes 15–25s; 10s causes false restarts.

No other changes to the frontend Dockerfile.

---

### 4. Frontend Health Route

**File**: `frontend/app/api/health/route.ts`

```typescript
import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({ status: "ok" });
}
```

This is a Next.js 14 App Router route. It:
- Returns `200 OK` with `{"status": "ok"}`
- Does not check DB, Redis, or any dependency — this is a **liveness** probe (is the process alive?), not readiness
- Works with `wget --spider` (which follows GET but checks HTTP status only)

**k8s probe alignment**: Kubernetes liveness probe will hit `/api/health`. Readiness probe will also hit `/api/health` initially; deep readiness (checking DB connectivity) is deferred to bolt 039 (k8s-config).

---

### 5. Backend `.dockerignore`

**File**: `backend/.dockerignore`

```
# Python artifacts
__pycache__
*.pyc
*.pyo
*.pyd
.mypy_cache
.ruff_cache

# uv / venv
.venv
.python-version

# Test artifacts
tests/
.pytest_cache
coverage.xml
.coverage

# Environment and secrets
.env
.env.*

# ML seed images (large, only for local dev)
seed-imgs/

# Git
.git
.gitignore

# Docs
*.md
README*
```

Key exclusions:
- `seed-imgs/` — local ML test images; can be hundreds of MB
- `.venv/` — the deps stage rebuilds this; copying from host would use the wrong platform's venv
- `tests/` — not needed in production image
- `.env*` — secrets must never bake into images

---

### 6. Frontend `.dockerignore` — Patch

The existing `frontend/.dockerignore` is missing `.env*`. Add one line:

```
# Add to existing frontend/.dockerignore:
.env
.env.*
.env.local
.env.production
```

---

### 7. Build Documentation

**File**: `CONTAINERS.md` (project root)

Covers: build commands, image naming convention, HEALTHCHECK behavior, local run instructions, registry push (pre-bolt 040), and layer caching tips.

---

### ADR Analysis

No new ADRs needed. This bolt implements established patterns:

| Pattern | Source |
|---------|--------|
| Alembic runs at deploy (not in image CMD) | ADR-030 |
| Multi-stage Docker builds | Industry standard; no project-specific tradeoff |
| Non-root uid 1001 | Security baseline; no project-specific tradeoff |

No decision with project-specific tradeoff warrants a new ADR entry.
