---
stage: test
bolt: 041-database-migrations
created: 2026-06-18T16:30:00Z
result: PASS
checks_total: 24
checks_passed: 24
checks_failed: 0
runtime_checks_pending: 5
---

## Test Report: Database Migrations

---

### Static Checks — 24/24 PASS

#### job.yaml (12 checks)

| # | Check | Result |
|---|-------|--------|
| 1 | `backoffLimit == 0` (ADR-037) | PASS |
| 2 | `activeDeadlineSeconds == 300` | PASS |
| 3 | `ttlSecondsAfterFinished == 3600` | PASS |
| 4 | `restartPolicy == Never` | PASS |
| 5 | `serviceAccountName == backend` | PASS |
| 6 | `command: [alembic, upgrade, head]` | PASS |
| 7 | `envFrom` includes configMapRef | PASS |
| 8 | `envFrom` includes secretRef | PASS |
| 9 | `IMAGE_TAG` placeholder in `image` field | PASS |
| 10 | `IMAGE_TAG` placeholder in `metadata.name` | PASS |
| 11 | `resources.requests` defined | PASS |
| 12 | `resources.limits` defined | PASS |

#### rollback-job.yaml.template (4 checks)

| # | Check | Result |
|---|-------|--------|
| 13 | `backoffLimit == 0` | PASS |
| 14 | `activeDeadlineSeconds == 120` | PASS |
| 15 | `command: [alembic, downgrade, -1]` | PASS |
| 16 | `IMAGE_TAG` placeholder in `image` field | PASS |

#### MIGRATIONS.md (8 checks)

| # | Check | Result |
|---|-------|--------|
| 17 | File exists and non-empty | PASS |
| 18 | Zero-downtime section present | PASS |
| 19 | Rollback procedure section present | PASS |
| 20 | Troubleshooting section present | PASS |
| 21 | 2-phase pattern documented | PASS |
| 22 | `alembic upgrade head` documented | PASS |
| 23 | `alembic downgrade` documented | PASS |
| 24 | References `rollback-job.yaml.template` | PASS |

---

### Runtime Checks — Deferred (require live k8s cluster)

| # | Check | Deferred to |
|---|-------|-------------|
| R1 | Migration Job completes successfully on clean DB | Manual / bolt 040 CI |
| R2 | Migration Job exits 0 when already at head (idempotency) | Manual / bolt 040 CI |
| R3 | Migration Job fails fast (`backoffLimit: 0`) on DB connection refused | Manual |
| R4 | Rollback Job downgrades one revision correctly | Manual rollback drill |
| R5 | `kubectl wait --timeout=300s` exits non-zero when Job fails | Manual / bolt 040 CI |

---

### Deliverables Verified

| File | Status |
|------|--------|
| `k8s/staging/migrations/job.yaml` | CREATED ✓ |
| `k8s/staging/migrations/rollback-job.yaml.template` | CREATED ✓ |
| `MIGRATIONS.md` (project root) | CREATED ✓ |
| `memory-bank/bolts/041-database-migrations/adr-037-migration-job-backoff-zero.md` | CREATED ✓ |
| `memory-bank/standards/decision-index.md` | UPDATED (37 total) ✓ |

---

### Notes

- `job.yaml` uses `envFrom: [configMapRef + secretRef]` (not just `DATABASE_URL`) because `core.config.settings` validates all required fields at import time via pydantic; missing vars cause `ValidationError` before alembic runs.
- `rollback-job.yaml.template` has `activeDeadlineSeconds: 120` (vs 300 for forward migration) because `downgrade -1` is a single-step, bounded operation.
- CI integration (submit → wait → deploy) is documented in `MIGRATIONS.md` and will be wired in bolt 040.
- `k8s/staging/migrations/` directory added; no gitignore entry needed (no secrets in these files; IMAGE_TAG is a placeholder, not a value).
