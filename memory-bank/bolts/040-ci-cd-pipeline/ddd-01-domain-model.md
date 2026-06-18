---
stage: domain-model
bolt: 040-ci-cd-pipeline
created: 2026-06-18T17:30:00Z
---

## Domain Model: CI/CD Pipeline

---

### Context Snapshot

| Item | State |
|------|-------|
| VCS | GitHub (repo: nicacommerce/virtual-closet assumed) |
| CI platform | GitHub Actions — no existing workflows |
| Container registry | ghcr.io (GitHub Container Registry) — native GitHub token auth |
| k8s cluster | Bare-metal k3s on Hetzner (no cloud OIDC provider) |
| k8s access from CI | kubeconfig stored as GitHub Actions secret (see ADR-038) |
| Image naming | `ghcr.io/{owner}/{service}:{env}-{sha7}` e.g. `ghcr.io/nicacommerce/backend:staging-a1b2c3d` |
| Backend tests | `pytest` with `asyncio_mode = auto`, files in `backend/tests/` |
| Frontend tests | No test runner — `next build` (type checking via TS compiler) + `eslint` |
| Migration Job | `k8s/staging/migrations/job.yaml` (bolt 041) — IMAGE_TAG placeholder |
| k8s manifests | `k8s/staging/` (bolt 039) — IMAGE_TAG placeholder in backend/frontend/celery |

**ghcr.io rationale**: GitHub Actions has first-class support — `GITHUB_TOKEN` suffices for push (no additional secrets). k3s pulls from ghcr.io using an imagePullSecret created once on cluster setup.

**kubeconfig vs GitHub OIDC**: GitHub OIDC token exchange for k8s requires a cloud provider webhook (AWS, GCP, Azure). Bare-metal k3s has no such webhook. Practical alternative: store k3s kubeconfig as a base64-encoded GitHub secret `KUBE_CONFIG_STAGING`. → ADR-038.

---

### Entities

#### `PRWorkflow`

Triggered on `pull_request` targeting `main`. No image push. Purpose: fast feedback gate before merge.

| Step | Tool | Notes |
|------|------|-------|
| Checkout | `actions/checkout@v4` | |
| Backend lint | `ruff check` in `./backend` | Via `uv run ruff` |
| Backend tests | `pytest backend/tests/` | Via `uv run pytest --timeout=60` |
| Frontend lint | `pnpm lint` in `./frontend` | Uses ESLint config |
| Frontend build | `pnpm build` in `./frontend` | Type-checks via TS; fails on type errors |
| Docker build (no push) | `docker build ./backend` + `docker build ./frontend` | Validates Dockerfile correctness |

Jobs run in two parallel groups:
- `backend-ci`: lint → test → docker build (backend)
- `frontend-ci`: lint → build → docker build (frontend)

PR is not mergeable unless both jobs pass (branch protection — story 010).

---

#### `DeployWorkflow`

Triggered on `push` to `main` (i.e., after PR merge). Executes the full deployment pipeline.

Steps in order:

```
1. Checkout + compute GIT_SHA (first 7 chars)
2. ghcr.io login (GITHUB_TOKEN)
3. backend-ci  ──┐ (parallel)
4. frontend-ci ──┘
5. Build + push backend image  ──┐ (parallel, after ci jobs)
6. Build + push frontend image ──┘
7. Configure kubeconfig (KUBE_CONFIG_STAGING secret)
8. Run migration Job (submit → wait 300s)
9. kubectl apply backend Deployment (IMAGE_TAG = GIT_SHA)
10. kubectl apply frontend Deployment + celery Deployment
11. kubectl rollout status (wait for pods Ready)
12. Health check gate (curl /health on backend + frontend)
13. Post result to GitHub commit status / PR comment
```

Steps 8–10 enforce the `DeploymentGate` invariant from bolt 041: migration MUST complete before app pods roll out.

---

#### `GHCRImagePush`

The artifact produced by steps 5/6 above.

| Attribute | Value |
|-----------|-------|
| Registry | `ghcr.io` |
| Backend tag | `ghcr.io/{owner}/backend:staging-{sha7}` |
| Frontend tag | `ghcr.io/{owner}/frontend:staging-{sha7}` |
| Latest tag | `ghcr.io/{owner}/backend:staging-latest` (also pushed) |
| Cache source | `staging-latest` — speeds up layer cache |
| Auth | `GITHUB_TOKEN` (no extra secret) |

The k8s manifests use the full `ghcr.io/` path after `sed` substitution in CI.

---

#### `KubeconfigAccess`

The mechanism for GitHub Actions runners to communicate with the staging k3s cluster.

| Attribute | Value |
|-----------|-------|
| Secret name | `KUBE_CONFIG_STAGING` |
| Format | base64-encoded `k3s.yaml` (kubeconfig) |
| Scope | GitHub repo secret (or environment secret for `staging` environment) |
| Setup | `echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > ~/.kube/config` |
| Access control | k3s RBAC — SA with permissions limited to `virtual-closet-staging` namespace |

→ ADR-038: kubeconfig secret over GitHub OIDC for bare-metal k3s.

---

#### `HealthCheckGate`

Post-deployment validation before marking the workflow as successful.

| Service | Endpoint | Expected | Timeout |
|---------|----------|----------|---------|
| backend | `https://api.staging.virtualcloset.io/health` | HTTP 200 | 60s |
| frontend | `https://staging.virtualcloset.io/api/health` | HTTP 200 `{"status":"ok"}` | 60s |

Implemented via `kubectl rollout status` (ensures pods are `Ready`) followed by `curl` probes against the public ingress. Both must pass; failure marks the workflow as failed and prevents PR from being auto-merged on re-runs.

---

#### `RollbackTrigger`

Manual workflow dispatch (`workflow_dispatch` event) that:
1. Accepts `previous_sha` as input
2. Runs the rollback Job (`rollback-job.yaml.template` with that SHA)
3. Re-deploys the previous image tag for backend, frontend, celery

Not automated — operator-triggered only.

---

#### `GitHubEnvironment`

GitHub Environments feature applied to the `DeployWorkflow`.

| Attribute | Value |
|-----------|-------|
| Name | `staging` |
| Protection rules | No approval required (auto-deploy on `main` push) |
| Secrets scope | `KUBE_CONFIG_STAGING` scoped to `staging` environment |
| URL | `https://staging.virtualcloset.io` |

Using a GitHub Environment unlocks deployment history, environment-scoped secrets, and the "Active deployments" view in the GitHub UI.

---

### Domain Rules

1. **PR workflow never pushes images** — push only on `main` merge
2. **Migration runs before Deployment rollout** — `kubectl wait job` exit code gates `kubectl apply deployment`
3. **Backend and frontend build in parallel** — no cross-dependency between image builds
4. **Health check gate is mandatory** — workflow fails (and notifies) if either endpoint is unhealthy post-deploy
5. **Image tags are immutable** — `staging-{sha7}` is never overwritten; `staging-latest` is a moving pointer for cache only
6. **kubeconfig access is namespace-scoped** — the SA used by the kubeconfig has no cluster-admin; only `virtual-closet-staging` namespace
7. **Rollback is manual** — no automated rollback on health check failure (operator decides; reduces risk of rollback loops)

---

### Relationships

```
PRWorkflow (on PR → main)
  ├── backend-ci:  ruff → pytest → docker build
  └── frontend-ci: eslint → next build → docker build

DeployWorkflow (on push → main)
  ├── backend-ci + frontend-ci  (same jobs, re-run)
  ├── GHCRImagePush (backend + frontend in parallel)
  ├── KubeconfigAccess
  ├── MigrationJob (bolt 041) ← DeploymentGate
  ├── kubectl apply (backend + frontend + celery)
  ├── kubectl rollout status
  ├── HealthCheckGate
  └── GitHubEnvironment (staging) ← deployment record

RollbackTrigger (workflow_dispatch, manual)
  ├── RollbackJob (bolt 041)
  └── kubectl apply (previous image)
```

---

### Scope

**In scope (this bolt):**
- `.github/workflows/pr.yaml` — PR build + test workflow
- `.github/workflows/deploy-staging.yaml` — staging deployment workflow
- `.github/workflows/rollback-staging.yaml` — manual rollback workflow
- `CI.md` (project root) — workflow guide, secrets setup, branch protection instructions, troubleshooting

**Out of scope:**
- Container registry creation (ghcr.io is auto-available for GitHub repos)
- imagePullSecret creation on k3s (one-time cluster setup, documented in `k8s/DEPLOY.md`)
- Production deployment workflow (manual gate; separate bolt)
- Self-hosted runners
- ADR: ghcr.io over alternatives → no ADR needed (obvious default for GitHub repos)

**ADRs to create in Stage 3:**
- **ADR-038**: kubeconfig secret over GitHub OIDC for bare-metal k3s access
