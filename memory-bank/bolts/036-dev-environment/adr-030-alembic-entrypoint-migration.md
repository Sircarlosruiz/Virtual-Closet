---
bolt: 036-dev-environment
created: 2026-06-17T16:00:00Z
status: accepted
superseded_by: null
---

# ADR-030: Alembic Migrations Run in Backend Entrypoint (Dev) / Kubernetes Job (Prod)

## Context

The dev environment needs database schema to be up-to-date every time `docker-compose up` is run, without requiring the developer to manually run `alembic upgrade head`. A decision was needed on where and how to trigger migrations automatically.

Three patterns exist for running migrations in containerized environments:
1. Backend application entrypoint (run migration before starting the app server)
2. Separate init container (Docker Compose: a dedicated service; k8s: an init container)
3. Manual step documented in the dev guide

The decision also has downstream consequences for bolt 039 (Kubernetes deployment config) and bolt 041 (database migrations), where the same question arises at a different scale.

## Decision

In **local development** (docker-compose): run `alembic upgrade head` inside the backend container's entrypoint script before starting uvicorn:

```sh
sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
```

In **production / k8s** (bolts 039, 041): run migrations as a dedicated Kubernetes Job that completes before the backend Deployment rolls out. Do NOT use the entrypoint pattern in production.

## Rationale

For **dev**: the entrypoint pattern is the simplest approach. The backend container already has the Python environment, `DATABASE_URL`, and Alembic config. Adding a separate service just for migrations adds compose complexity without benefit in a single-developer local environment. The failure mode (migration fails → container exits → developer sees error in logs) is acceptable and clear.

For **prod / k8s**: the entrypoint pattern is explicitly rejected because it creates a race condition when multiple backend replicas start simultaneously (all would try to run migrations), and it couples schema migration to app deployment in a way that makes rollbacks fragile.

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected (dev) |
|-------------|------|------|--------------------|
| Separate compose service (`migration-runner`) | Clear separation of concerns | Adds a service; must share Python env or duplicate image | Unnecessary complexity for single-dev local env |
| Manual step in dev guide | Zero compose complexity | Developer must remember to run it; common source of "why is my schema wrong?" | Friction degrades dev experience |
| k8s-style init container in compose | Mirrors production pattern | Compose `init` containers are clunky; adds config duplication | Over-engineering for dev |

## Consequences

### Positive

- `docker-compose up` is truly one command — schema is always current
- No separate service or manual step for developers
- Migration errors are immediately visible in `docker-compose logs backend`
- `alembic upgrade head` is idempotent — safe to run on every restart

### Negative

- Backend container startup is slightly slower (migration check adds ~1-3 seconds)
- If backend and celery_worker share the same image, only the backend runs migrations (celery entrypoint must NOT run migrations — this must be documented)
- Pattern diverges from production (k8s Job) — developers must understand the two approaches

### Risks

- **Risk**: Developer mistakes celery_worker entrypoint and adds migration there too, causing double-run. **Mitigation**: Document clearly in dev guide that only the `backend` service runs migrations; celery command must not include `alembic upgrade head`.
- **Risk**: Long-running migration blocks backend startup beyond health check timeout. **Mitigation**: Set generous `start_period: 30s` on backend health check; document for migrations over 30s.

## Related

- **Stories**: 002-configure-alembic-auto, 006-test-dev-startup
- **Standards**: Applies to dev environment only; k8s pattern deferred to bolt 041
- **Previous ADRs**: ADR-013 (multi-step Alembic migration with backfill strategy — read when designing new migrations that run via this entrypoint pattern)
