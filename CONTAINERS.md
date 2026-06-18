# Container Build Guide

Docker images for the Virtual Closet frontend (Next.js 16) and backend (FastAPI).

## Quick Reference

| Service | Dockerfile | Base | Strategy |
|---------|-----------|------|----------|
| frontend | `frontend/Dockerfile` | node:22-alpine | 4-stage: base → deps → builder → runner |
| backend | `backend/Dockerfile` | python:3.13-slim | 3-stage: base → deps → runner |

## Building Images

```bash
# Backend
docker build -t virtual-closet/backend:latest ./backend

# Frontend
docker build -t virtual-closet/frontend:latest ./frontend

# With specific tag (use git SHA in CI)
GIT_SHA=$(git rev-parse --short HEAD)
docker build -t virtual-closet/backend:staging-${GIT_SHA} ./backend
docker build -t virtual-closet/frontend:staging-${GIT_SHA} ./frontend
```

## Image Naming Convention

```
virtual-closet/{service}:{env}-{git-sha-7}
```

Examples:
- `virtual-closet/backend:staging-a1b2c3d`
- `virtual-closet/frontend:production-f9e8d7c`

**`latest` is banned in production k8s manifests** — always use a specific tag.

## After Updating Backend Dependencies

Any change to `backend/pyproject.toml` or `backend/uv.lock` requires regenerating the lockfile before building:

```bash
cd backend
uv lock
cd ..
docker build -t virtual-closet/backend:dev ./backend
```

## Health Endpoints

Both images expose a health endpoint used by Docker `HEALTHCHECK` and Kubernetes probes:

| Service | Path | Response |
|---------|------|----------|
| backend | `GET /health` | `{"status": "ok"}` |
| frontend | `GET /api/health` | `{"status": "ok"}` |

These are **liveness** probes only — they do not check database or Redis connectivity. Readiness probes (with dependency checks) are configured in Kubernetes manifests (see bolt 039).

## HEALTHCHECK Behavior

Docker restarts a container after `retries` consecutive failures past `start_period`.

| Service | interval | timeout | start_period | retries |
|---------|----------|---------|--------------|---------|
| frontend | 30s | 10s | 30s | 3 |
| backend | 30s | 10s | 20s | 3 |

`start_period` accounts for cold-start time before health checks begin counting failures.

## Security

Both production images run as non-root:

| Service | User | UID | GID |
|---------|------|-----|-----|
| frontend | nextjs | 1001 | 1001 (nodejs) |
| backend | fastapi | 1001 | 1001 |

## Expected Image Sizes

| Service | Expected | Notes |
|---------|----------|-------|
| frontend (runner stage) | ~150–200MB | Next.js standalone strips unused code |
| backend (runner stage) | ~600–800MB | `rembg[cpu]` + `opencv-python-headless` are runtime deps (~400MB combined) |

The backend image size is a known constraint of the current dependency structure. Separating ML inference deps into an optional uv group is a future optimization.

## Layer Caching

Layer invalidation is optimized in both images:

**Frontend** — only `pnpm install` reruns when `package.json` / `pnpm-lock.yaml` changes; code-only changes skip the deps stage entirely.

**Backend** — only `uv sync` reruns when `pyproject.toml` / `uv.lock` changes; code-only changes skip the deps stage.

To exploit this in CI, always pass `--cache-from` pointing to the previous image:

```bash
docker build \
  --cache-from virtual-closet/backend:staging-latest \
  -t virtual-closet/backend:staging-${GIT_SHA} \
  ./backend
```

## Running Locally (Without Docker Compose)

```bash
# Backend
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  virtual-closet/backend:latest

# Frontend
docker run --rm -p 3000:3000 \
  virtual-closet/frontend:latest
```

For full local development with hot-reload, use `docker compose up` instead (see [DEVELOPMENT.md](DEVELOPMENT.md)).

## Base Image Updates

The base images (`python:3.13-slim`, `node:22-alpine`) receive periodic security patches. Update them by:

1. Changing the `FROM` tag in the Dockerfile (or using digest pinning for reproducibility)
2. Rebuilding and running `trivy image virtual-closet/backend:latest` to verify no critical CVEs
3. Committing the updated Dockerfile

Base image CVE scanning is automated in CI (bolt 040).
