# Local Development Guide

Get the full development environment running with a single command.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2 on Linux)
- Git
- NVIDIA GPU + drivers (optional — required only for local AI inference)

No Node.js or Python installation required on your machine.

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd virtual_closet

# 2. Create your local environment file
cp backend/.env.example backend/.env

# 3. Start all services
docker compose up
```

The first run downloads Docker images and builds containers (~5–10 minutes).
Subsequent starts take under 2 minutes.

## What Starts

| Service | URL | Credentials |
|---------|-----|------------|
| Frontend (Next.js) | http://localhost:3000 | — |
| Backend API (FastAPI) | http://localhost:8000 | — |
| API docs (Swagger) | http://localhost:8000/docs | — |
| PostgreSQL | localhost:5432 | `postgres` / `postgres` |
| Redis | localhost:6379 | no password |
| RabbitMQ management | http://localhost:15672 | `guest` / `guest` |
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin` |

## Startup Order

Services start in a health-gated sequence:

```
postgres + redis + rabbitmq + minio  →  (all healthy)
        fastapi  →  (migrations run, then /health passes)
        celery_worker + frontend
```

Database migrations (`alembic upgrade head`) run automatically inside the `fastapi` container before the server starts. You never need to run migrations manually in dev.

## Hot Reload

Both services reload automatically when you save files — no container restart needed.

**Frontend**: Next.js Fast Refresh — browser updates within ~1 second. Page state is preserved on most changes.

**Backend**: uvicorn `--reload` — API server restarts within ~2 seconds on any `.py` change.

> If hot reload stops responding, run `docker compose restart fastapi` or `docker compose restart frontend`.

## Adding Dependencies

### Backend (Python)

```bash
# Enter the running container
docker compose exec fastapi bash

# Install with uv
uv add <package>

# The .venv inside the container is mounted as a named volume.
# Restart the service to pick up the new package.
exit
docker compose restart fastapi
```

### Frontend (Node.js)

After changing `package.json`, rebuild the frontend image to update the `node_modules` named volume:

```bash
docker compose build frontend
docker compose up frontend
```

> Why? The `frontend_node_modules` volume is populated at build time. A plain `restart` won't reinstall packages. See [ADR-031](memory-bank/bolts/036-dev-environment/adr-031-node-modules-named-volume-overlay.md).

## Database Migrations

Migrations run automatically on every `docker compose up`. To create a new migration:

```bash
docker compose exec fastapi bash
uv run alembic revision --autogenerate -m "describe your change"
exit
```

The new file appears in `backend/alembic/versions/`. Commit it and it will auto-apply on the next `docker compose up`.

> **Celery workers do not run migrations.** Only the `fastapi` service runs `alembic upgrade head`. See [ADR-030](memory-bank/bolts/036-dev-environment/adr-030-alembic-entrypoint-migration.md).

## GPU / AI Inference (Optional)

Requires an NVIDIA GPU with drivers installed.

```bash
# FASHN VTON v1.5 (~8 GB VRAM)
docker compose --profile gpu up fashn

# TryOff garment extraction (FLUX.2-klein, ~18 GB — needs 24 GB VRAM)
docker compose --profile tryoff up tryoff-model
```

Set `VTON_PROVIDER=fashn_local` in `backend/.env` to route try-on jobs to the local GPU.

First run downloads model weights (~2–18 GB depending on service). Weights are cached in named volumes and reused on subsequent starts.

## Environment Variables

All configuration lives in `backend/.env` (gitignored). The template is `backend/.env.example`.

Key variables to configure for full functionality:

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | Auto-set by docker-compose for Docker mode |
| `REDIS_URL` | ✅ | Auto-set by docker-compose for Docker mode |
| `JWT_SECRET_KEY` | ✅ | Change from default for anything beyond local dev |
| `RESEND_API_KEY` | Optional | Set `EMAIL_BACKEND=console` to log emails to stdout instead |
| `TWO_FACTOR_ENCRYPTION_KEY` | Optional | Required if using 2FA (TOTP/SMS). Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `REPLICATE_API_KEY` | Optional | Cloud VTON inference (replicate provider) |
| `HF_TOKEN` | Optional | HuggingFace gated models (TryOff FLUX) |

> Variables set explicitly in `docker-compose.yml` (e.g. `DATABASE_URL`, `REDIS_URL`) override `backend/.env` when running in Docker.

## Useful Commands

```bash
# Start all services in background
docker compose up -d

# View logs for a specific service
docker compose logs -f fastapi
docker compose logs -f celery_worker

# Restart a single service (picks up env changes)
docker compose restart fastapi

# Stop everything
docker compose down

# Stop and delete volumes (full reset — loses database data)
docker compose down -v

# Force clean reinstall of frontend node_modules
docker volume rm virtual_closet_frontend_node_modules
docker compose up frontend
```

## Troubleshooting

**`docker compose up` hangs on fastapi startup**
Check backend logs: `docker compose logs fastapi`. If migrations are running a long backfill, increase `start_period` in the fastapi health check or wait.

**`/health` returns 502 / frontend can't reach backend**
FastAPI may still be running migrations. Check `docker compose logs fastapi` for `alembic upgrade head` output.

**Frontend changes not reflecting in browser**
Polling hot-reload is active but can lag. Hard refresh (`Ctrl+Shift+R`) or restart the frontend service: `docker compose restart frontend`.

**`Module not found` error in frontend container**
The `frontend_node_modules` volume may be stale after `package.json` changes. Rebuild:
```bash
docker compose build frontend && docker compose up frontend
```

**Port already in use**
Another process is using one of the mapped ports. Find it with `lsof -i :<port>` (macOS/Linux) or `netstat -ano | findstr :<port>` (Windows) and stop it.

**On WSL2 (Windows)**
- Docker Desktop must be running with WSL2 integration enabled for your distro
- Store the repo inside the WSL2 filesystem (`~/dev/...`), not on the Windows filesystem (`/mnt/c/...`), for acceptable I/O performance

**On Apple Silicon (M-series Mac)**
All images use `linux/amd64`. Docker Desktop's Rosetta 2 emulation handles this automatically. GPU profiles are not available on Apple Silicon.
