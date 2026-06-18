---
stage: technical-design
bolt: 041-database-migrations
created: 2026-06-18T16:15:00Z
---

## Technical Design: Database Migrations

---

### Deliverables

| File | Type | Action |
|------|------|--------|
| `k8s/staging/migrations/job.yaml` | k8s manifest | CREATE |
| `k8s/staging/migrations/rollback-job.yaml.template` | k8s template | CREATE |
| `MIGRATIONS.md` | Project-root guide | CREATE |

---

### `k8s/staging/migrations/job.yaml`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: alembic-migrate-IMAGE_TAG
  namespace: virtual-closet-staging
  labels:
    app.kubernetes.io/name: alembic-migrate
    app.kubernetes.io/component: migration
    app.kubernetes.io/version: "IMAGE_TAG"
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: alembic-migrate
        app.kubernetes.io/component: migration
    spec:
      restartPolicy: Never
      serviceAccountName: backend
      containers:
        - name: migrate
          image: virtual-closet/backend:IMAGE_TAG
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: virtual-closet-config
            - secretRef:
                name: virtual-closet-secrets
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 200m
              memory: 512Mi
```

#### Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `backoffLimit: 0` | 0 | ADR-037 — partial migration + auto-retry → second attempt fails with misleading error |
| `activeDeadlineSeconds: 300` | 300s | Matches `kubectl wait --timeout`; prevents hung pod blocking pipeline indefinitely |
| `ttlSecondsAfterFinished: 3600` | 1h | Auto-cleanup; logs remain long enough for post-deploy inspection |
| `restartPolicy: Never` | Never | Pod stays in Failed state so operator can `kubectl logs` |
| `envFrom: configMapRef + secretRef` | Both | `core.config.settings` validates ALL fields at import time; partial env → `pydantic.ValidationError` before alembic runs |
| `serviceAccountName: backend` | Reuse backend SA | No additional k8s API access needed; backend SA already exists |
| `resources` (100m/256Mi req, 200m/512Mi lim) | Lower than Deployment | Short-lived; not serving traffic |
| `name: alembic-migrate-IMAGE_TAG` | SHA in name | Unique per deployment; prevents collision across TTL window |

---

### `k8s/staging/migrations/rollback-job.yaml.template`

```yaml
# Rollback one migration revision.
# Usage:
#   sed "s/IMAGE_TAG/${GIT_SHA}/g" rollback-job.yaml.template | kubectl create -f -
# IMAGE_TAG = tag of the image that APPLIED the migration (new image, not old).
# The new image contains the downgrade() function for the revision being undone.
apiVersion: batch/v1
kind: Job
metadata:
  name: alembic-rollback-IMAGE_TAG
  namespace: virtual-closet-staging
  labels:
    app.kubernetes.io/name: alembic-rollback
    app.kubernetes.io/component: migration
    app.kubernetes.io/version: "IMAGE_TAG"
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: alembic-rollback
        app.kubernetes.io/component: migration
    spec:
      restartPolicy: Never
      serviceAccountName: backend
      containers:
        - name: rollback
          image: virtual-closet/backend:IMAGE_TAG
          command: ["alembic", "downgrade", "-1"]
          envFrom:
            - configMapRef:
                name: virtual-closet-config
            - secretRef:
                name: virtual-closet-secrets
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 200m
              memory: 512Mi
```

**Why IMAGE_TAG = new (forward) image**: The `downgrade()` function lives in the migration file added by the new image. The old image does not contain that revision file and cannot run `downgrade` for it.

---

### CI Integration Sequence (consumed by bolt 040)

```bash
# Delete previous job for this SHA (Jobs are immutable — kubectl apply errors on existing Job)
kubectl delete job alembic-migrate-${GIT_SHA} \
  -n virtual-closet-staging --ignore-not-found

# Submit migration Job
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/migrations/job.yaml \
  | kubectl create -f -

# Block pipeline until complete (timeout = activeDeadlineSeconds)
kubectl wait --for=condition=complete \
  job/alembic-migrate-${GIT_SHA} \
  -n virtual-closet-staging \
  --timeout=300s
# Non-zero exit → pipeline halts; Deployment rollout does NOT proceed

# Only on success: update application images
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/backend/deployment.yaml \
  | kubectl apply -f -
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/frontend/deployment.yaml \
  | kubectl apply -f -
```

`delete --ignore-not-found` before `create` provides clean re-run semantics when the same SHA is redeployed (e.g., hotfix re-push to same tag).

---

### `MIGRATIONS.md` — Section Outline

| Section | Content |
|---------|---------|
| Authoring a migration | `alembic revision --autogenerate -m "..."`, review output, never remove `downgrade()` |
| Zero-downtime rules | Expandable vs contractable changes; 2-phase pattern for column renames/drops |
| Running locally | `docker compose exec backend alembic upgrade head` |
| Running on staging | Manual `sed + kubectl create` for out-of-band execution |
| Rollback procedure | Step-by-step: scale backend to 0 → apply rollback Job → re-deploy old image |
| Troubleshooting | Job Pending, alembic lock table, revision conflicts, connection refused |

---

### ADRs to create in Stage 3

- **ADR-037**: `backoffLimit: 0` on Alembic migration Job
