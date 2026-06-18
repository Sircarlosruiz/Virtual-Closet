---
stage: domain-model
bolt: 036-dev-environment
created: 2026-06-17T15:30:00Z
---

## Static Model: dev-environment

### Entities

- **DevEnvironment**: Properties: compose_version, services[], volumes[], networks[], env_file_path — Business Rules: every service referenced in `depends_on` must be declared; no circular dependencies; single `docker-compose up` must start all services
- **Service**: Properties: name, image, build_context, command, ports[], volumes[], env_vars[], depends_on[], health_check, restart_policy — Business Rules: name must be unique within DevEnvironment; services with `depends_on` must wait for dependency health before starting
- **MigrationJob**: Properties: target_revision ("head"), connection_url, alembic_config_path, auto_run — Business Rules: runs after PostgreSQL is healthy; idempotent (`alembic upgrade head` safe to re-run); must fail loudly on error
- **HotReloadConfig**: Properties: service_name, watch_paths[], poll_interval_ms, mode (inotify | polling) — Business Rules: bind-mount of source directory must exist; host path maps to container path; mode defaults to polling in Docker Desktop (inotify unreliable)
- **EnvironmentVariable**: Properties: name, default_value, required, sensitive, description — Business Rules: required vars with no default must be present in `.env` before compose starts; sensitive vars must never have real values in `.env.example`

---

### Value Objects

- **ServicePort**: host_port (int), container_port (int) — Constraints: host_port must be available on host machine; uniqueness enforced at DevEnvironment level
- **VolumeMount**: source (host path or named volume), target (container path), mode (rw | ro) — Constraints: bind-mount source path must exist; named volume is auto-created by Docker
- **HealthCheck**: test (command), interval, timeout, retries — Constraints: test command must exit 0 for healthy; retry count determines startup grace period
- **ReloadTrigger**: file_pattern (glob), debounce_ms — Constraints: pattern must be specific enough to avoid false positives; debounce prevents reload storm on bulk saves

---

### Aggregates

- **DevEnvironment** (Aggregate Root): Members: Service[], Volume[], Network[] — Invariants: all `depends_on` references resolve to declared services; no port conflicts across services; all required EnvironmentVariables declared in `.env.example`
- **BackendService** (sub-aggregate of DevEnvironment): Members: Service (backend), HotReloadConfig (uvicorn --reload), MigrationJob — Invariants: MigrationJob must complete before BackendService accepts traffic; uvicorn --reload bound to `/backend` bind-mount
- **FrontendService** (sub-aggregate of DevEnvironment): Members: Service (frontend), HotReloadConfig (Next.js Fast Refresh) — Invariants: Next.js dev server must run `npm run dev`; `/frontend` bind-mount must preserve node_modules via named volume overlay

---

### Domain Events

- **ServiceHealthy**: Trigger: Docker health check passes — Payload: service_name, timestamp
- **MigrationCompleted**: Trigger: `alembic upgrade head` exits 0 — Payload: revisions_applied[], duration_ms
- **MigrationFailed**: Trigger: `alembic upgrade head` exits non-0 — Payload: error_message, last_successful_revision
- **HotReloadTriggered**: Trigger: file change detected in watch_paths — Payload: file_path, service_name, reload_type (fast-refresh | server-restart)
- **EnvironmentValidationFailed**: Trigger: required env var missing at compose startup — Payload: missing_vars[]
- **ObsoleteServiceRemoved**: Trigger: catvton service entry deleted from compose — Payload: service_name ("catvton"), volumes_removed (["catvton_cache"])

---

### Domain Services

- **MigrationOrchestrator**: Runs `alembic upgrade head` after PostgreSQL becomes healthy; waits on `postgres` health check before executing; reports MigrationCompleted or MigrationFailed; Dependencies: PostgreSQL service, Alembic config, DATABASE_URL env var
- **HotReloadService**: Manages file-watch → reload loop for both backend (uvicorn --reload) and frontend (Next.js Fast Refresh); Dependencies: bind-mounted source directories, HotReloadConfig per service
- **EnvironmentValidator**: Compares `.env` against `.env.example` keys; raises EnvironmentValidationFailed for missing required vars; runs before any service starts; Dependencies: EnvironmentVariable[]
- **ServiceOrchestrator**: Respects `depends_on` + health checks to enforce startup order: postgres → (migrations) → backend → (celery) → frontend; Dependencies: DevEnvironment, HealthCheck per service

---

### Repository Interfaces

- **ServiceConfigRepository**: Entity: Service — Methods: get_all(): Service[], get_by_name(name: str): Service, validate_ports(): PortConflict[]
- **EnvironmentVariableRepository**: Entity: EnvironmentVariable — Methods: load_from_example(): EnvironmentVariable[], load_from_env(): dict[str, str], get_missing_required(): str[]
- **VolumeRepository**: Entity: Volume — Methods: get_all(): Volume[], get_obsolete(): Volume[] (finds catvton_cache), prune_unused(): void

---

### Ubiquitous Language

- **docker-compose up**: The single command that starts all development services in the correct order
- **hot-reload**: Automatic server/browser refresh when source files change, without container restart
- **Fast Refresh**: Next.js 14's hot-reload mechanism that preserves component state
- **uvicorn --reload**: FastAPI development server flag enabling automatic restart on `.py` file changes
- **alembic upgrade head**: Command that applies all pending Alembic migrations to the latest revision
- **catvton**: The obsolete virtual try-on service (CatVTON) being removed from the compose configuration
- **catvton_cache**: The Docker named volume associated with the catvton service, also being removed
- **bind mount**: Docker volume type that maps a host filesystem directory directly into a container, enabling hot-reload
- **named volume**: Docker-managed persistent volume (e.g., `postgres_data`, `node_modules_cache`) — survives container restarts
- **node_modules overlay**: Named volume mounted at `/frontend/node_modules` to prevent host node_modules from overwriting container-installed packages
- **.env.example**: Version-controlled template declaring all required environment variable names with placeholder values
- **depends_on**: Docker Compose directive that enforces service startup ordering with health check conditions
- **health check**: Docker mechanism (e.g., `pg_isready`, `curl /health`) that signals when a service is ready to accept traffic
- **dev environment**: The full local Docker Compose setup, encompassing postgres, minio, rabbitmq, redis, celery_worker, backend, frontend
- **GPU service**: The AI inference service (fashn/flux models) requiring NVIDIA Titan RTX; GPU support kept for local dev (per ADR-003, weights downloaded at build time)
- **polling mode**: Hot-reload mechanism using periodic file system polling instead of inotify, required for Docker Desktop on macOS/Windows
