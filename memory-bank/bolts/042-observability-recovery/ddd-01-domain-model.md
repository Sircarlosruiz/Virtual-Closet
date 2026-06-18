---
stage: domain-model
bolt: 042-observability-recovery
created: 2026-06-18T21:00:00Z
---

## Domain Model: Observability & Recovery

---

### Context Snapshot

| Item | State |
|------|-------|
| Backend | FastAPI; uses `logging.getLogger(__name__)`; `TokenRefreshMiddleware` pattern in `core/middleware.py` |
| Frontend | Next.js 16.2.6; no `middleware.ts` yet |
| Alerting stack | None (Phase 1 = GitHub Actions scheduled cron; Phase 2 = Prometheus + Grafana) |
| Log storage | Pod stdout → k3s node journal (`journalctl`); no aggregation platform in Phase 1 |
| Backups | PostgreSQL data on local-path PV (Hetzner disk); no automated backup configured yet |
| Rollback | `kubectl rollout undo` + bolt 040 rollback workflow (`rollback-staging.yaml`) |

**Phase 1 scope** (this bolt): request ID tracing, health monitor scheduled workflow, operational runbook.
**Phase 2 deferred**: Loki/Grafana log aggregation, Prometheus metrics, advanced tracing (Jaeger).

---

### Entities

#### `RequestTrace`

A UUID (`uuid4`) generated per HTTP request, used to correlate log lines across service layers.

| Attribute | Value |
|-----------|-------|
| Format | UUID4 string (e.g., `550e8400-e29b-41d4-a716-446655440000`) |
| Header name | `X-Request-ID` |
| Generation | Backend middleware — if header already set by client or upstream proxy, preserve it; else generate |
| Propagation | Set on response; backend logs emit it with every log line for that request |
| Frontend | Next.js middleware reads `X-Request-ID` from backend proxy response and echoes it in server-side logs |

---

#### `RequestIDMiddleware`

A new FastAPI `BaseHTTPMiddleware` in `backend/core/middleware.py` (appended alongside `TokenRefreshMiddleware`).

| Behaviour | Detail |
|-----------|--------|
| On each request | Read `X-Request-ID` from incoming headers; if absent, generate `str(uuid4())` |
| Context storage | Store in Python `contextvars.ContextVar` (`_request_id_var`) so any log call in the same request coroutine can read it |
| Response header | Set `X-Request-ID` on the response |
| Log format | Configure `logging.basicConfig(format=...)` in `main.py` to include `%(request_id)s` via a custom `logging.Filter` that reads from the ContextVar |

Pattern: follows `TokenRefreshMiddleware` — `BaseHTTPMiddleware`, registered in `main.py` via `app.add_middleware(RequestIDMiddleware)`.

---

#### `FrontendRequestPropagation`

Next.js `middleware.ts` (project root of `frontend/`) — runs on every request via the Next.js Edge Runtime.

| Behaviour | Detail |
|-----------|--------|
| On incoming request | Read `X-Request-ID` from request headers; if present (set by browser JS or upstream), pass through; else generate new UUID |
| Forward to backend | API proxy routes pass the header to the backend (Next.js `fetch` with `headers` forwarded) |
| Response | Echo `X-Request-ID` in response headers so browser devtools can correlate |
| Matcher | `config.matcher` excludes static assets (`/_next/static`, `/favicon.ico`, etc.) |

---

#### `HealthMonitorWorkflow`

A GitHub Actions scheduled workflow (`.github/workflows/health-monitor.yaml`) that polls the public endpoints every 15 minutes and opens a GitHub Issue on failure.

| Attribute | Value |
|-----------|-------|
| Schedule | `*/15 * * * *` (cron, every 15 minutes) |
| Endpoints checked | `https://api.staging.virtualcloset.io/health` + `https://staging.virtualcloset.io/api/health` |
| Failure action | `gh issue create` — title `🚨 Staging health check failed`, body includes timestamps and HTTP status codes |
| Recovery action | After creating an issue, exit non-zero so GitHub marks the workflow run as failed (visible in UI) |
| Deduplication | Check if an open issue with the same title already exists; if so, add a comment instead of creating a duplicate |

This covers story 004 (pod crash → health endpoint returns non-200) and story 005 (node offline → connection refused). Both manifest as endpoint unavailability.

---

#### `RolloutRecovery`

Pod-level recovery using Kubernetes native facilities.

| Action | Command |
|--------|---------|
| View deployment history | `kubectl rollout history deployment/{name} -n virtual-closet-staging` |
| Undo last rollout | `kubectl rollout undo deployment/{name} -n virtual-closet-staging` |
| Undo to specific revision | `kubectl rollout undo deployment/{name} --to-revision=N -n virtual-closet-staging` |
| Monitor | `kubectl rollout status deployment/{name} -n virtual-closet-staging` |

For migration-involved rollbacks: use the bolt 040 `rollback-staging.yaml` workflow — it handles both schema downgrade and image revert.

---

#### `DatabaseBackup`

Manual + scheduled backup of the PostgreSQL StatefulSet using `pg_dump`.

| Attribute | Value |
|-----------|-------|
| Source | `postgres-0` pod in `virtual-closet-staging` |
| Command | `kubectl exec postgres-0 -- pg_dump -U postgres virtualcloset | gzip > backup-YYYY-MM-DD.sql.gz` |
| Destination | Operator machine; optionally upload to Hetzner Object Storage |
| Schedule | Manually before every production-impacting operation; automated weekly via cron (out of scope for Phase 1 code — documented procedure only) |
| Restore | `kubectl exec -i postgres-0 -- psql -U postgres virtualcloset < backup.sql` |

---

#### `DisasterRecoveryRunbook`

Collected in `RECOVERY.md` at the project root.

| Section | Content |
|---------|---------|
| Pod crash | Check liveness probes, `kubectl describe`, `kubectl logs`, `kubectl rollout undo` |
| Node failure | Force-delete stuck pods, drain node, schedule replacement |
| Database corrupted | Scale backend to 0, restore from backup, scale back |
| Full cluster rebuild | Re-apply all manifests in order (from `k8s/DEPLOY.md`), restore DB, re-run migrations |
| Phase 2 observability | What comes next: Loki + Promtail, Prometheus, Grafana, Jaeger |

---

### Domain Rules

1. **Request ID is always present on outbound responses** — middleware generates one if client doesn't send it
2. **Backend logs include request ID on every line** — via `logging.Filter` reading from `ContextVar`
3. **Health monitor opens ONE issue per incident** — deduplication via `gh issue list` before `gh issue create`
4. **Rollout undo is the first recovery action** — schema-safe (old image + current schema, if migration was backward-compatible); migration rollback only when undo alone is insufficient
5. **DB backup before destructive operations** — documented as required step in recovery runbook
6. **Phase 2 explicitly scoped** — no Prometheus/Grafana/Loki code in this bolt; only documented as future work

---

### Relationships

```
RequestTrace
  ├── RequestIDMiddleware (backend/core/middleware.py — new class)
  │    └── ContextVar _request_id_var → logging.Filter → all log lines
  └── FrontendRequestPropagation (frontend/middleware.ts — new file)

HealthMonitorWorkflow (.github/workflows/health-monitor.yaml)
  ├── polls /health endpoints every 15min
  └── opens GitHub Issue on failure

RolloutRecovery → documented in RECOVERY.md → bolt 040 rollback-staging.yaml
DatabaseBackup  → documented in RECOVERY.md
DisasterRecoveryRunbook → RECOVERY.md
```

---

### Scope

**In scope (this bolt):**
- `backend/core/middleware.py` — append `RequestIDMiddleware` class
- `backend/main.py` — register `RequestIDMiddleware` + configure log format
- `frontend/middleware.ts` — Next.js Edge middleware for `X-Request-ID`
- `.github/workflows/health-monitor.yaml` — scheduled health check + issue alerting
- `RECOVERY.md` — complete disaster recovery runbook

**Out of scope:**
- Loki, Promtail, Grafana, Prometheus, Jaeger → Phase 2
- Automated DB backup cron → Phase 2
- PagerDuty / on-call integration → Phase 2
- Log retention configuration → Phase 2

**No new ADRs**: All choices are clear defaults (UUID4, ContextVar, GitHub Issues for alerting) with no significant alternatives requiring formal decision.
