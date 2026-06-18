---
stage: domain-model
bolt: 041-database-migrations
created: 2026-06-18T15:45:00Z
---

## Domain Model: Database Migrations

---

### Context Snapshot

| Item | State |
|------|-------|
| Alembic setup | `backend/alembic/` — async engine, reads `DATABASE_URL` from `core.config.settings` |
| Migration files | 22 revisions in `backend/alembic/versions/` |
| Dev pattern | ADR-030: `alembic upgrade head` in backend entrypoint before `uvicorn` |
| Prod pattern | ADR-030: k8s Job runs before backend Deployment rollout |
| DB | PostgreSQL 16 (StatefulSet in `virtual-closet-staging`, bolt 039) |
| Backend image | `virtual-closet/backend:IMAGE_TAG` — contains `alembic`, `alembic.ini`, `alembic/` at `/app` |

The `alembic upgrade head` command is already idempotent — if the schema is already at head, it exits 0 without any writes.

---

### Entities

#### `MigrationJob`

A k8s `batch/v1 Job` that applies all pending Alembic revisions to completion.

| Attribute | Value | Notes |
|-----------|-------|-------|
| `image` | `virtual-closet/backend:IMAGE_TAG` | Same image as backend; contains alembic binary |
| `command` | `["alembic", "upgrade", "head"]` | Runs in `/app` (WORKDIR) |
| `restartPolicy` | `Never` | On failure: stop; don't retry automatically |
| `backoffLimit` | `0` | Zero retries — see ADR-037 |
| `activeDeadlineSeconds` | `300` | 5-minute hard timeout |
| `ttlSecondsAfterFinished` | `3600` | Auto-delete Job after 1 hour |
| `env` | `DATABASE_URL` from Secret | Only env var needed for alembic |
| `name` | `alembic-migrate-{IMAGE_TAG}` | Unique per deployment |

**Why `backoffLimit: 0`**: If a migration partially applies (e.g., adds a column but fails mid-transaction), retrying may attempt to add the already-existing column and fail with a different error. Operators must inspect state before retrying. → ADR-037.

**Why the same image**: The migration script (`env.py`) imports `core.config`, `core.database`, and all models (`from models import Base`). These imports must match the schema of the new migrations being applied. Using the new image guarantees the ORM models match the new migration files.

---

#### `MigrationRevision`

A single Alembic revision file in `backend/alembic/versions/`.

| Attribute | Type | Notes |
|-----------|------|-------|
| `revision_id` | string | 12-char hex (e.g., `0c2cff14de00`) |
| `down_revision` | string or tuple | parent revision(s); null for initial |
| `upgrade()` | function | DDL operations to apply |
| `downgrade()` | function | DDL operations to reverse |
| `is_backward_compatible` | bool | MUST be true for zero-downtime deploys |

**Backward compatibility constraint** (zero-downtime invariant):
When the migration Job runs (new schema applied), the old backend pods (previous image) are still serving traffic. The migration must not break the old backend. Rules:

| Change type | Allowed? | Notes |
|-------------|----------|-------|
| Add nullable column | ✅ | Old code ignores; new code reads default |
| Add column WITH DEFAULT | ✅ | Old inserts use default |
| Add table | ✅ | Old code ignores unknown tables |
| Add index | ✅ | Transparent to app |
| Rename column | ❌ | Old code references old name |
| Drop column (old code uses it) | ❌ | Old code breaks |
| Add NOT NULL without DEFAULT | ❌ | Old inserts break |
| Change column type | ⚠️ | Only if both types are compatible |

---

#### `RollbackJob`

A k8s Job identical to `MigrationJob` but with `command: ["alembic", "downgrade", "-1"]`.

| Attribute | Value | Notes |
|-----------|-------|-------|
| `command` | `["alembic", "downgrade", "-1"]` | One step back |
| `name` | `alembic-rollback-{IMAGE_TAG}` | Created imperatively by operator, not committed |
| `backoffLimit` | `0` | Same as migration — fail fast |

Rollback is an operator action, not an automated one. A `rollback-job.yaml.template` is committed for reference; operators copy and apply it when needed.

---

#### `DeploymentGate`

The ordering constraint that ensures migrations complete before backend pods start serving traffic.

```
MigrationJob → [complete: 0 failures] → Backend Deployment rollout
                      ↓ [failure]
                CI pipeline stops; backend NOT updated
```

In CI/CD (bolt 040), this is enforced with:
```bash
kubectl wait --for=condition=complete job/alembic-migrate-{SHA} --timeout=300s
# Only proceeds to kubectl apply deployment.yaml if exit code 0
```

---

#### `MigrationValidation`

Pre-flight checks run before the Job is submitted (in CI, bolt 040):

| Check | Command | Purpose |
|-------|---------|---------|
| DB reachable | `kubectl exec postgres-0 -- pg_isready -U postgres` | Fail fast if DB is down |
| Current head | `alembic current` (via exec on running backend pod) | Document pre-migration state for audit |
| Pending count | `alembic history --indicate-current` | Warn if many pending migrations |

These are advisory — the migration Job itself handles connectivity failures gracefully (exits non-zero → `backoffLimit: 0` → Job fails → CI stops).

---

### Domain Rules

1. **`backoffLimit: 0`** — no automatic retries on migration failure; operator must inspect and act (ADR-037)
2. **`restartPolicy: Never`** — pod is not restarted on failure; a new Job must be created to retry
3. **Migration Job uses same image as backend Deployment** — guarantees ORM models match migration files
4. **All new migrations MUST be backward-compatible** — zero-downtime invariant; enforced by code review
5. **Job name includes IMAGE_TAG** — prevents duplicate Job names across deployments; old Jobs are auto-cleaned by TTL
6. **`alembic upgrade head` is idempotent** — safe to run even if already at head; exits 0
7. **Rollback is manual** — automated downgrade risks data loss; operator creates rollback Job after inspection

---

### Relationships

```
DeploymentGate
  ├── MigrationJob          (batch/v1 Job; must complete before Deployment rollout)
  │    ├── image: backend:IMAGE_TAG
  │    ├── command: alembic upgrade head
  │    └── env: DATABASE_URL (from Secret)
  ├── MigrationRevision[]   (files in backend/alembic/versions/)
  └── RollbackJob           (created imperatively by operator when needed)

MigrationValidation         (pre-flight; CI step before Job submission)
```

---

### Scope

**In scope (this bolt):**
- `k8s/staging/migrations/job.yaml` — migration Job template with `IMAGE_TAG` placeholder
- `k8s/staging/migrations/rollback-job.yaml.template` — rollback template
- `MIGRATIONS.md` (project root) — migration authoring guide + zero-downtime rules + troubleshooting

**Out of scope:**
- CI integration wiring (Job submit + wait) → bolt 040
- New migration files → developer workflow
- Production environment manifests → after staging is proven
