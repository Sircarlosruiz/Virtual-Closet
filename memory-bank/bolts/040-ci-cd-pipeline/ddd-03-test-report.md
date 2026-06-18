---
stage: test
bolt: 040-ci-cd-pipeline
created: 2026-06-18T18:15:00Z
result: PASS
checks_total: 40
checks_passed: 40
checks_failed: 0
runtime_checks_pending: 5
---

## Test Report: CI/CD Pipeline

---

### Static Checks — 40/40 PASS

#### `.github/workflows/pr.yaml` (9 checks)

| # | Check | Result |
|---|-------|--------|
| 1 | Parses as valid YAML | PASS |
| 2 | Triggers on `pull_request → main` | PASS |
| 3 | `backend-ci` has `postgres:16` service container | PASS |
| 4 | `backend-ci` runs `ruff check` | PASS |
| 5 | `backend-ci` runs `pytest` | PASS |
| 6 | `backend-ci` has `DATABASE_URL` env var | PASS |
| 7 | `frontend-ci` runs lint | PASS |
| 8 | `frontend-ci` runs build | PASS |
| 9 | Docker build has `push: false` | PASS |

#### `.github/workflows/deploy-staging.yaml` (13 checks)

| # | Check | Result |
|---|-------|--------|
| 10 | Parses as valid YAML | PASS |
| 11 | Triggers on `push → main` | PASS |
| 12 | `push-images` needs `[backend-ci, frontend-ci]` | PASS |
| 13 | `push-images` has `packages: write` permission | PASS |
| 14 | `push-images` outputs `sha7` | PASS |
| 15 | `deploy` job uses `staging` environment | PASS |
| 16 | `deploy` job needs `push-images` | PASS |
| 17 | `deploy` runs migration Job (`alembic-migrate`) | PASS |
| 18 | `deploy` waits for migration (`kubectl wait`) | PASS |
| 19 | `deploy` applies `backend/deployment.yaml` | PASS |
| 20 | `deploy` applies `frontend/deployment.yaml` | PASS |
| 21 | `deploy` has health check gate | PASS |
| 22 | `deploy` uses `KUBE_CONFIG_STAGING` | PASS |

#### `.github/workflows/rollback-staging.yaml` (7 checks)

| # | Check | Result |
|---|-------|--------|
| 23 | Parses as valid YAML | PASS |
| 24 | Triggers on `workflow_dispatch` | PASS |
| 25 | Has `image_sha` input | PASS |
| 26 | Has `target_sha` input | PASS |
| 27 | Scales backend to 0 (`--replicas=0`) | PASS |
| 28 | Runs rollback Job (`rollback-job.yaml.template`) | PASS |
| 29 | Has health check gate | PASS |

#### k8s manifest patches (4 checks)

| # | Check | Result |
|---|-------|--------|
| 30 | `k8s/staging/backend/deployment.yaml` has `ghcr-pull-secret` | PASS |
| 31 | `k8s/staging/frontend/deployment.yaml` has `ghcr-pull-secret` | PASS |
| 32 | `k8s/staging/celery/deployment.yaml` has `ghcr-pull-secret` | PASS |
| 33 | `k8s/staging/migrations/job.yaml` has `ghcr-pull-secret` | PASS |

#### `backend/pyproject.toml` (1 check)

| # | Check | Result |
|---|-------|--------|
| 34 | `ruff` in `[dependency-groups] dev` | PASS |

#### `CI.md` (6 checks)

| # | Check | Result |
|---|-------|--------|
| 35 | File exists | PASS |
| 36 | `KUBE_CONFIG_STAGING` setup documented | PASS |
| 37 | `ghcr-pull-secret` setup documented | PASS |
| 38 | Branch protection documented | PASS |
| 39 | Rollback workflow documented | PASS |
| 40 | Troubleshooting section present | PASS |

---

### Notes on YAML parsing

PyYAML (YAML 1.1) parses the `on:` key as Python boolean `True`. The test script was adjusted to use `doc.get(True, {})` for trigger parsing. The workflow files themselves are correct GitHub Actions YAML — GitHub's parser uses YAML 1.2 where `on` is a string.

---

### Runtime Checks — Deferred (require live GitHub Actions runner + k3s cluster)

| # | Check | Deferred to |
|---|-------|-------------|
| R1 | PR workflow blocks merge on test failure | Manual / first PR |
| R2 | Image push to ghcr.io succeeds with GITHUB_TOKEN | First merge to main |
| R3 | `kubectl wait` gates Deployment rollout on migration success | First deploy |
| R4 | Health check gate catches unhealthy pods | First deploy + deliberate failure test |
| R5 | Rollback workflow completes in < 120s | Manual rollback drill |

---

### Deliverables Verified

| File | Status |
|------|--------|
| `.github/workflows/pr.yaml` | CREATED ✓ |
| `.github/workflows/deploy-staging.yaml` | CREATED ✓ |
| `.github/workflows/rollback-staging.yaml` | CREATED ✓ |
| `CI.md` | CREATED ✓ |
| `backend/pyproject.toml` | PATCHED (ruff added) ✓ |
| `k8s/staging/backend/deployment.yaml` | PATCHED (imagePullSecrets) ✓ |
| `k8s/staging/frontend/deployment.yaml` | PATCHED (imagePullSecrets) ✓ |
| `k8s/staging/celery/deployment.yaml` | PATCHED (imagePullSecrets) ✓ |
| `k8s/staging/migrations/job.yaml` | PATCHED (imagePullSecrets) ✓ |
| `memory-bank/bolts/040-ci-cd-pipeline/adr-038-*` | CREATED ✓ |
| `memory-bank/standards/decision-index.md` | UPDATED (38 total) ✓ |
