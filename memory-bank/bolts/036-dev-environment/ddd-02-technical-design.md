---
stage: technical-design
bolt: 036-dev-environment
created: 2026-06-17T15:45:00Z
---

## Technical Design: dev-environment

---

### Architecture Pattern

**Selected Pattern**: Service Mesh with Health-Gated Startup Ordering

Docker Compose v2 format with `depends_on: condition: service_healthy` gates to enforce a deterministic startup sequence. Alembic migrations run as a one-shot command inside the backend container's entrypoint script, not as a separate init container, to avoid duplicating the Python environment.

**Rationale**:
- `depends_on: condition: service_healthy` is the only reliable way to sequence startup in Compose without external scripts
- Running migrations in the backend entrypoint keeps the Python environment and `DATABASE_URL` in one place
- Polling-based hot-reload (configurable via `WATCHFILES_FORCE_POLLING=true`) ensures cross-platform compatibility (Docker Desktop on macOS/Windows)

---

### Layer Structure

```text
┌─────────────────────────────────────────────────────────────┐
│  Developer Machine (Host)                                    │
│  ./frontend/  ./backend/  .env                              │
└───────────────────┬─────────────────────────────────────────┘
                    │ bind mounts (hot-reload)
┌───────────────────▼─────────────────────────────────────────┐
│  Docker Compose Network: app_network                        │
│                                                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  postgres  │  │   redis    │  │      rabbitmq        │  │
│  │  :5432     │  │  :6379     │  │  :5672 / :15672      │  │
│  │  healthck: │  │  healthck: │  │  healthck:           │  │
│  │  pg_isready│  │  redis-cli │  │  rabbitmq-diag       │  │
│  └──────┬─────┘  └─────┬──────┘  └──────────┬───────────┘  │
│         │ healthy       │ healthy             │ healthy      │
│         ▼               │                     │              │
│  ┌────────────────────┐ │                     │              │
│  │ backend (FastAPI)  │◄┘                     │              │
│  │  entrypoint:       │                       │              │
│  │  1. alembic upgrade│                       │              │
│  │  2. uvicorn --reload                       │              │
│  │  :8000             │◄──────────────────────┘              │
│  └──────┬─────────────┘                                     │
│         │ healthy (/health)                                   │
│         ▼                                                    │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │  celery_worker     │  │  frontend (Next.js) │             │
│  │  depends: backend  │  │  npm run dev        │             │
│  │          rabbitmq  │  │  :3000              │             │
│  └────────────────────┘  └────────────────────┘             │
│                                                             │
│  ┌────────────────────┐                                     │
│  │  minio             │  (independent, no startup dep)      │
│  │  :9000 / :9001     │                                     │
│  └────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
```

**Startup Order**:
1. `postgres`, `redis`, `rabbitmq`, `minio` — start in parallel (no deps)
2. `backend` — waits for `postgres: healthy`, `redis: healthy`, `rabbitmq: healthy`; runs Alembic migrations in entrypoint, then starts uvicorn
3. `celery_worker` — waits for `backend: healthy`, `rabbitmq: healthy`
4. `frontend` — no strict dep on backend (can start in parallel with backend)

---

### Service Definitions

#### postgres

```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  ports:
    - "5432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s
```

#### redis

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
```

#### rabbitmq

```yaml
rabbitmq:
  image: rabbitmq:3-management-alpine
  environment:
    RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
    RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
  ports:
    - "5672:5672"
    - "15672:15672"
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "ping"]
    interval: 10s
    timeout: 10s
    retries: 5
    start_period: 30s
```

#### minio

```yaml
minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
  volumes:
    - minio_data:/data
  ports:
    - "9000:9000"
    - "9001:9001"
```

#### backend (FastAPI + Alembic)

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.dev
  command: >
    sh -c "alembic upgrade head &&
           uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app"
  volumes:
    - ./backend:/app                        # bind mount for hot-reload
  environment:
    DATABASE_URL: ${DATABASE_URL}
    REDIS_URL: ${REDIS_URL}
    RABBITMQ_URL: ${RABBITMQ_URL}
    WATCHFILES_FORCE_POLLING: "true"        # polling for Docker Desktop compat
  ports:
    - "8000:8000"
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

**Dockerfile.dev** (backend — minimal, hot-reload focused):
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# No COPY . . — source mounted via bind mount at runtime
```

#### celery_worker

```yaml
celery_worker:
  build:
    context: ./backend
    dockerfile: Dockerfile.dev
  command: celery -A celery_app worker --loglevel=info -Q vton,tryoff,default
  volumes:
    - ./backend:/app
  environment:
    DATABASE_URL: ${DATABASE_URL}
    REDIS_URL: ${REDIS_URL}
    RABBITMQ_URL: ${RABBITMQ_URL}
  depends_on:
    backend:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
```

#### frontend (Next.js)

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile.dev
  command: npm run dev
  volumes:
    - ./frontend:/app                        # bind mount for hot-reload
    - frontend_node_modules:/app/node_modules # named volume overlay — preserves container packages
  environment:
    NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
    CHOKIDAR_USEPOLLING: "true"              # polling for Docker Desktop compat
  ports:
    - "3000:3000"
```

**Dockerfile.dev** (frontend — minimal, hot-reload focused):
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
# No COPY . . — source mounted via bind mount at runtime
```

---

### Volume Strategy

| Volume Name | Type | Purpose | Survives Restart |
|-------------|------|---------|-----------------|
| `postgres_data` | Named | PostgreSQL data files | ✅ Yes |
| `minio_data` | Named | Object storage data | ✅ Yes |
| `frontend_node_modules` | Named | node_modules overlay | ✅ Yes |
| `./backend` → `/app` | Bind | Backend source (hot-reload) | N/A |
| `./frontend` → `/app` | Bind | Frontend source (hot-reload) | N/A |

**node_modules Overlay Pattern**: The `frontend_node_modules` named volume mounted at `/app/node_modules` shadows the bind-mounted host directory's `node_modules` (which may be absent or have wrong platform packages). This ensures the container-installed packages are always used.

**Removed Volumes** (from catvton era):
- `catvton_cache` — remove from volumes section
- Any `catvton_network` entries — remove if present

---

### Migration Automation Design

**Mechanism**: Backend entrypoint runs `alembic upgrade head` before `uvicorn` starts.

```text
Backend Container Startup
          │
          ▼
  [postgres: healthy] ──► [alembic upgrade head]
          │                       │
          │                  success? ──► [uvicorn --reload]
          │                       │
          │                  failure? ──► container exits with non-0
          │                               (compose logs show error)
          ▼
  backend: healthy  (after /health returns 200)
```

**Idempotency**: `alembic upgrade head` is safe to re-run — it checks current revision and is a no-op if already at head.

**Failure behavior**: If migration fails, the backend container exits. Docker Compose does not restart it (no `restart: always` in dev). The developer sees the error in `docker-compose logs backend`.

---

### Hot-Reload Design

#### Backend (FastAPI / uvicorn)

```text
Host: ./backend/*.py  ──► bind mount ──► /app/*.py (container)
                                              │
                                     uvicorn --reload-dir /app
                                              │
                              WATCHFILES_FORCE_POLLING=true
                              (polling every 500ms, reliable on all platforms)
                                              │
                                     file changed → server restart
                                     (< 2 seconds typical)
```

#### Frontend (Next.js)

```text
Host: ./frontend/**  ──► bind mount ──► /app/** (container)
                                              │
                                     Next.js Fast Refresh (built-in)
                                              │
                              CHOKIDAR_USEPOLLING=true
                              (polling for Docker Desktop compat)
                                              │
                                     file changed → HMR update
                                     state preserved (React Fast Refresh)
```

---

### Environment Variable Design

#### .env.example Structure

```bash
# ─── PostgreSQL ─────────────────────────────────────────────────
POSTGRES_DB=virtual_closet_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password          # ⚠ INSECURE: dev only
DATABASE_URL=postgresql+asyncpg://postgres:dev_password@postgres:5432/virtual_closet_dev

# ─── Redis ──────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── RabbitMQ ───────────────────────────────────────────────────
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=dev_password          # ⚠ INSECURE: dev only
RABBITMQ_URL=amqp://admin:dev_password@rabbitmq:5672/

# ─── MinIO ──────────────────────────────────────────────────────
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin          # ⚠ INSECURE: dev only
MINIO_ENDPOINT=http://minio:9000
MINIO_BUCKET=virtual-closet

# ─── Frontend ───────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000

# ─── Auth (JWT) ─────────────────────────────────────────────────
# Generate with: openssl genrsa -out private.pem 2048
JWT_PRIVATE_KEY=<paste RSA private key here>
JWT_PUBLIC_KEY=<paste RSA public key here>
SECRET_KEY=dev-secret-key-change-in-prod  # ⚠ INSECURE: dev only

# ─── AI / GPU (optional: requires NVIDIA GPU) ───────────────────
# Leave blank if no GPU available (VTON features will be unavailable locally)
REPLICATE_API_TOKEN=<your token here>
```

**Validation rules**:
- `DATABASE_URL`, `REDIS_URL`, `RABBITMQ_URL` — required (backend exits without them)
- `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` — required for auth endpoints
- `REPLICATE_API_TOKEN` — optional (GPU inference degrades gracefully)

---

### Security Design

- **Scope**: Dev-only security — intentionally permissive, clearly documented
- `⚠ INSECURE: dev only` comments on all default credentials in `.env.example`
- `.env` added to `.gitignore` (never committed)
- `.env.example` committed without real secrets (placeholder values only)
- No TLS in dev (services communicate on internal Docker network `app_network`)
- Redis has no password in dev (acceptable; not exposed externally beyond port 6379)
- Per ADR-026: `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` env vars required for RS256 auth — `.env.example` must document the `openssl genrsa` generation command

---

### NFR Implementation

| NFR | Requirement | Design Approach |
|-----|------------|-----------------|
| Startup time | < 5 minutes from `docker-compose up` | Parallel startup of postgres/redis/rabbitmq/minio; backend waits only for health gates |
| Hot-reload latency | < 2 seconds for code changes | uvicorn polling (500ms) + Next.js Fast Refresh (HMR) |
| Developer onboarding | < 30 minutes from clone to running | `.env.example` + single command + DEVELOPMENT.md guide |
| Cross-platform | macOS, Windows (WSL2), Linux | Polling mode for file watching (`WATCHFILES_FORCE_POLLING`, `CHOKIDAR_USEPOLLING`) |
| Idempotent restarts | `docker-compose restart` safe | Alembic upgrade is idempotent; named volumes persist data |
| GPU optional | AI features optional locally | `REPLICATE_API_TOKEN` optional; graceful degradation documented |

---

### Integration Points

| Integration | Dev Configuration | Notes |
|-------------|------------------|-------|
| PostgreSQL | `postgres:5432` (internal), `localhost:5432` (host) | Alembic and SQLAlchemy both use `DATABASE_URL` |
| Redis | `redis:6379` (internal), `localhost:6379` (host) | Session denylist (ADR-016, ADR-023); no password in dev |
| RabbitMQ | `rabbitmq:5672` (Celery), `localhost:15672` (mgmt UI) | Queues: `vton`, `tryoff`, `default` per ADR-004 |
| MinIO | `minio:9000` (S3 API), `localhost:9001` (console) | Bucket auto-created via init script or backend startup |
| Stripe | No local integration | Use Stripe test keys from `.env`; webhook forwarding via `stripe listen` (separate) |
