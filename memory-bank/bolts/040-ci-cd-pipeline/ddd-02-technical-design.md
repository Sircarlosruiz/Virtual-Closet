---
stage: technical-design
bolt: 040-ci-cd-pipeline
created: 2026-06-18T17:45:00Z
---

## Technical Design: CI/CD Pipeline

---

### Deliverables

| File | Action |
|------|--------|
| `.github/workflows/pr.yaml` | CREATE — PR build + test |
| `.github/workflows/deploy-staging.yaml` | CREATE — staging deployment |
| `.github/workflows/rollback-staging.yaml` | CREATE — manual rollback |
| `CI.md` | CREATE — secrets setup, branch protection, troubleshooting |
| `backend/pyproject.toml` | PATCH — add `ruff` to `[dependency-groups] dev` |
| `k8s/staging/backend/deployment.yaml` | PATCH — add `imagePullSecrets: [{name: ghcr-pull-secret}]` |
| `k8s/staging/frontend/deployment.yaml` | PATCH — add `imagePullSecrets` |
| `k8s/staging/celery/deployment.yaml` | PATCH — add `imagePullSecrets` |
| `k8s/staging/migrations/job.yaml` | PATCH — add `imagePullSecrets` |

---

### Action version pins

| Action | Version | Reason |
|--------|---------|--------|
| `actions/checkout` | `v4` | Current major |
| `astral-sh/setup-uv` | `v4` | Current major; enables uv cache |
| `actions/setup-node` | `v4` | Current major |
| `pnpm/action-setup` | `v4` | Matches pnpm lockfile v9.0 |
| `docker/setup-buildx-action` | `v3` | BuildKit support |
| `docker/login-action` | `v3` | Current major |
| `docker/build-push-action` | `v6` | Current major |

---

### `.github/workflows/pr.yaml`

```yaml
name: PR

on:
  pull_request:
    branches: [main]

jobs:
  backend-ci:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: virtual_closet_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock

      - name: Install dependencies
        run: uv sync --frozen
        working-directory: ./backend

      - name: Lint
        run: uv run ruff check .
        working-directory: ./backend

      - name: Test
        run: uv run pytest tests/ --timeout=60 -q
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test
          JWT_SECRET_KEY: ci-only-not-a-real-secret-key-32chars
          JWT_ALGORITHM: HS256
          TWO_FACTOR_ENCRYPTION_KEY: Y2ktb25seS10d28tZmFjdG9yLWtleS0zMmNoYXJz
          FRONTEND_URL: http://localhost:3000
          BACKEND_URL: http://localhost:8000
          COOKIE_SECURE: "false"
          MINIO_ENDPOINT: http://localhost:9000
          MINIO_ACCESS_KEY: minioadmin
          MINIO_SECRET_KEY: minioadmin
          MINIO_BUCKET_NAME: virtual-closet-test
          REDIS_URL: redis://localhost:6379/0
          RABBITMQ_URL: amqp://guest:guest@localhost:5672/
          REPLICATE_API_KEY: r8_ci_placeholder
          RESEND_API_KEY: re_ci_placeholder
          VTON_PROVIDER: replicate

      - uses: docker/setup-buildx-action@v3

      - name: Docker build (validate)
        run: docker build ./backend

  frontend-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Install dependencies
        run: pnpm install --frozen-lockfile
        working-directory: ./frontend

      - name: Lint
        run: pnpm lint
        working-directory: ./frontend

      - name: Build (type check)
        run: pnpm build
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
          NEXT_PUBLIC_BACKEND_URL: http://localhost:8000

      - uses: docker/setup-buildx-action@v3

      - name: Docker build (validate)
        run: docker build ./frontend
```

**Test service containers analysis:**
- PostgreSQL 16: required — `conftest.py` hardcodes `postgresql+asyncpg://postgres:postgres@localhost:5432/virtual_closet_test`
- Redis: NOT required — `limiter.reset()` is in-memory; no Redis fixture in conftest
- RabbitMQ: NOT required — `mock_celery` fixture patches `celery_app.send_task`; no actual RabbitMQ connection
- MinIO: NOT required — no MinIO fixture in conftest; storage calls mocked at test level

---

### `.github/workflows/deploy-staging.yaml`

```yaml
name: Deploy Staging

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  NAMESPACE: virtual-closet-staging

permissions:
  contents: read
  packages: write

jobs:
  backend-ci:
    # identical to pr.yaml backend-ci job
    uses: ./.github/workflows/pr.yaml  # reuse via workflow_call (or duplicate)

  frontend-ci:
    # identical to pr.yaml frontend-ci job
    uses: ./.github/workflows/pr.yaml

  push-images:
    needs: [backend-ci, frontend-ci]
    runs-on: ubuntu-latest
    outputs:
      sha7: ${{ steps.sha.outputs.sha7 }}
    steps:
      - uses: actions/checkout@v4

      - id: sha
        run: echo "sha7=${GITHUB_SHA::7}" >> $GITHUB_OUTPUT

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/backend:staging-${{ steps.sha.outputs.sha7 }}
            ghcr.io/${{ github.repository_owner }}/backend:staging-latest
          cache-from: type=registry,ref=ghcr.io/${{ github.repository_owner }}/backend:staging-latest
          cache-to: type=inline

      - name: Build and push frontend
        uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/frontend:staging-${{ steps.sha.outputs.sha7 }}
            ghcr.io/${{ github.repository_owner }}/frontend:staging-latest
          cache-from: type=registry,ref=ghcr.io/${{ github.repository_owner }}/frontend:staging-latest
          cache-to: type=inline

  deploy:
    needs: [push-images]
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.virtualcloset.io
    env:
      SHA7: ${{ needs.push-images.outputs.sha7 }}
      OWNER: ${{ github.repository_owner }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      - name: Run migration job
        run: |
          kubectl delete job alembic-migrate-${SHA7} \
            -n ${NAMESPACE} --ignore-not-found
          sed "s/IMAGE_TAG/${SHA7}/g" k8s/staging/migrations/job.yaml \
            | sed "s|virtual-closet/backend:|ghcr.io/${OWNER}/backend:|g" \
            | kubectl create -f -
          kubectl wait --for=condition=complete \
            job/alembic-migrate-${SHA7} \
            -n ${NAMESPACE} --timeout=300s

      - name: Deploy backend + celery
        run: |
          for f in k8s/staging/backend/deployment.yaml k8s/staging/celery/deployment.yaml; do
            sed "s/IMAGE_TAG/${SHA7}/g" ${f} \
              | sed "s|virtual-closet/backend:|ghcr.io/${OWNER}/backend:|g" \
              | kubectl apply -f -
          done

      - name: Deploy frontend
        run: |
          sed "s/IMAGE_TAG/${SHA7}/g" k8s/staging/frontend/deployment.yaml \
            | sed "s|virtual-closet/frontend:|ghcr.io/${OWNER}/frontend:|g" \
            | kubectl apply -f -

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/backend \
            -n ${NAMESPACE} --timeout=120s
          kubectl rollout status deployment/celery \
            -n ${NAMESPACE} --timeout=120s
          kubectl rollout status deployment/frontend \
            -n ${NAMESPACE} --timeout=120s

      - name: Health check gate
        run: |
          for i in $(seq 1 12); do
            B=$(curl -sf --max-time 10 \
              https://api.staging.virtualcloset.io/health \
              -o /dev/null -w "%{http_code}" || echo "000")
            F=$(curl -sf --max-time 10 \
              https://staging.virtualcloset.io/api/health \
              -o /dev/null -w "%{http_code}" || echo "000")
            echo "Attempt ${i}/12: backend=${B} frontend=${F}"
            if [ "${B}" = "200" ] && [ "${F}" = "200" ]; then
              echo "Health checks passed"
              exit 0
            fi
            sleep 10
          done
          echo "Health check failed after 120s"
          kubectl logs -l app.kubernetes.io/name=backend \
            -n ${NAMESPACE} --tail=50 || true
          exit 1
```

**Note on CI job reuse**: Rather than using `workflow_call` (which requires converting pr.yaml to a reusable workflow), duplicate the backend-ci and frontend-ci jobs in deploy-staging.yaml. This is simpler and avoids workflow nesting complexity. PR workflow and deploy workflow are independent — they both run full CI.

---

### `.github/workflows/rollback-staging.yaml`

```yaml
name: Rollback Staging

on:
  workflow_dispatch:
    inputs:
      image_sha:
        description: 'SHA of the image that applied the bad migration (7 chars)'
        required: true
      target_sha:
        description: 'Previous good image SHA to redeploy (7 chars)'
        required: true

env:
  NAMESPACE: virtual-closet-staging
  OWNER: ${{ github.repository_owner }}

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.virtualcloset.io
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG_STAGING }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      - name: Scale backend to zero
        run: |
          kubectl scale deployment/backend \
            --replicas=0 -n ${NAMESPACE}

      - name: Run rollback migration job
        run: |
          IMAGE_SHA="${{ inputs.image_sha }}"
          sed "s/IMAGE_TAG/${IMAGE_SHA}/g" \
            k8s/staging/migrations/rollback-job.yaml.template \
            | sed "s|virtual-closet/backend:|ghcr.io/${OWNER}/backend:|g" \
            | kubectl create -f -
          kubectl wait --for=condition=complete \
            job/alembic-rollback-${IMAGE_SHA} \
            -n ${NAMESPACE} --timeout=120s

      - name: Redeploy previous image
        run: |
          TARGET="${{ inputs.target_sha }}"
          for f in k8s/staging/backend/deployment.yaml k8s/staging/celery/deployment.yaml; do
            sed "s/IMAGE_TAG/${TARGET}/g" ${f} \
              | sed "s|virtual-closet/backend:|ghcr.io/${OWNER}/backend:|g" \
              | kubectl apply -f -
          done
          sed "s/IMAGE_TAG/${TARGET}/g" k8s/staging/frontend/deployment.yaml \
            | sed "s|virtual-closet/frontend:|ghcr.io/${OWNER}/frontend:|g" \
            | kubectl apply -f -

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/backend \
            -n ${NAMESPACE} --timeout=120s
          kubectl rollout status deployment/celery \
            -n ${NAMESPACE} --timeout=120s
          kubectl rollout status deployment/frontend \
            -n ${NAMESPACE} --timeout=120s

      - name: Health check gate
        run: |
          for i in $(seq 1 12); do
            B=$(curl -sf --max-time 10 \
              https://api.staging.virtualcloset.io/health \
              -o /dev/null -w "%{http_code}" || echo "000")
            F=$(curl -sf --max-time 10 \
              https://staging.virtualcloset.io/api/health \
              -o /dev/null -w "%{http_code}" || echo "000")
            echo "Attempt ${i}/12: backend=${B} frontend=${F}"
            if [ "${B}" = "200" ] && [ "${F}" = "200" ]; then
              echo "Rollback succeeded"
              exit 0
            fi
            sleep 10
          done
          echo "Rollback health check failed — manual intervention required"
          exit 1
```

---

### Manifest patches (Stage 4)

**`imagePullSecrets` required on all 4 manifests** because ghcr.io packages are private by default for private GitHub repos.

Patch to add to `spec.template.spec` in backend, frontend, celery deployments:
```yaml
      imagePullSecrets:
        - name: ghcr-pull-secret
```

Same patch for `spec.template.spec` in `k8s/staging/migrations/job.yaml`.

The `ghcr-pull-secret` is a one-time cluster setup step (documented in CI.md):
```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<PAT-with-read:packages> \
  -n virtual-closet-staging
```

**`ruff` in pyproject.toml dev group** — patch to `backend/pyproject.toml`:
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "ruff>=0.9.0",
]
```

---

### ADR to create in Stage 3

- **ADR-038**: kubeconfig secret over GitHub OIDC for bare-metal k3s — GitHub OIDC requires a cloud IAM provider webhook; k3s has none; kubeconfig stored as base64-encoded GitHub environment secret is the practical alternative.
