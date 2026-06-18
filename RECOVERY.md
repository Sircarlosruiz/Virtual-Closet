# Disaster Recovery Runbook

Operational procedures for the Virtual Closet staging environment. For CI/CD rollbacks see [CI.md](CI.md); for schema rollbacks see [MIGRATIONS.md](MIGRATIONS.md).

---

## Pod rollback (application regression)

Use when the latest deployment broke the application but no schema changes were applied, or when the migration was backward-compatible.

```bash
export NS=virtual-closet-staging
export SVC=backend  # or: frontend, celery

# 1. View rollout history
kubectl rollout history deployment/${SVC} -n ${NS}

# 2. Undo to the previous revision
kubectl rollout undo deployment/${SVC} -n ${NS}

# 3. Monitor until pods are Ready
kubectl rollout status deployment/${SVC} -n ${NS} --timeout=120s

# 4. Verify health
curl -sf https://api.staging.virtualcloset.io/health
```

To undo to a specific revision (e.g., revision 3):
```bash
kubectl rollout undo deployment/${SVC} --to-revision=3 -n ${NS}
```

If the migration was NOT backward-compatible, use the [CI.md § Manual rollback](CI.md) procedure instead — it handles schema downgrade before image revert.

---

## Pod crash loop

```bash
export NS=virtual-closet-staging
export POD=$(kubectl get pods -n ${NS} -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Inspect events
kubectl describe pod ${POD} -n ${NS}

# Read logs from the crashed container
kubectl logs ${POD} -n ${NS} --previous

# Common causes and fixes:
# - OOMKilled: increase memory limit in deployment.yaml and redeploy
# - CrashLoopBackOff + env error: check secrets/configmap values
# - ImagePullBackOff: check ghcr-pull-secret, image tag exists
```

---

## Node failure

When a k3s worker node goes offline:

```bash
# 1. Identify stuck pods (status: Terminating or Unknown)
kubectl get pods -n virtual-closet-staging -o wide

# 2. Force-delete stuck pods so k8s reschedules them
kubectl delete pod <pod-name> -n virtual-closet-staging --grace-period=0 --force

# 3. If node is permanently lost, remove it from the cluster
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
kubectl delete node <node-name>
```

> StatefulSet pods (postgres, minio, rabbitmq) use `local-path` PVs — their data is tied to the node. If the worker node is gone, those PVs are gone. Restore from backup (see below).

---

## Database backup

Run before any destructive operation (data migration, cluster rebuild, major upgrade).

```bash
export NS=virtual-closet-staging
export BACKUP_FILE="virtualcloset-$(date +%Y-%m-%d).sql.gz"

# Dump from running postgres-0 pod
kubectl exec postgres-0 -n ${NS} -- \
  pg_dump -U postgres virtualcloset \
  | gzip > ${BACKUP_FILE}

echo "Backup written to ${BACKUP_FILE} ($(du -sh ${BACKUP_FILE} | cut -f1))"
```

Store the backup off-cluster (e.g., Hetzner Object Storage, local machine, or encrypted S3-compatible store). Do NOT store it only on the same Hetzner server — if the server fails, the backup is lost too.

---

## Database restore

```bash
export NS=virtual-closet-staging
export BACKUP_FILE="virtualcloset-YYYY-MM-DD.sql.gz"

# 1. Scale backend and celery to zero (stop all writes)
kubectl scale deployment/backend --replicas=0 -n ${NS}
kubectl scale deployment/celery --replicas=0 -n ${NS}

# 2. Drop and recreate the database
kubectl exec postgres-0 -n ${NS} -- \
  psql -U postgres -c "DROP DATABASE IF EXISTS virtualcloset;"
kubectl exec postgres-0 -n ${NS} -- \
  psql -U postgres -c "CREATE DATABASE virtualcloset;"

# 3. Restore from backup
gunzip -c ${BACKUP_FILE} \
  | kubectl exec -i postgres-0 -n ${NS} -- \
    psql -U postgres virtualcloset

# 4. Run migrations to ensure schema is at head
# (only needed if restoring an older backup)
export GIT_SHA=<current-backend-image-sha>
kubectl delete job alembic-migrate-${GIT_SHA} -n ${NS} --ignore-not-found
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/migrations/job.yaml \
  | sed "s|virtual-closet/backend:|ghcr.io/${OWNER}/backend:|g" \
  | kubectl create -f -
kubectl wait --for=condition=complete \
  job/alembic-migrate-${GIT_SHA} -n ${NS} --timeout=300s

# 5. Scale backend and celery back up
kubectl scale deployment/backend --replicas=2 -n ${NS}
kubectl scale deployment/celery --replicas=1 -n ${NS}

# 6. Health check
curl -sf https://api.staging.virtualcloset.io/health
```

---

## Full cluster rebuild

When the entire k3s cluster must be rebuilt from scratch (server destroyed, OS reinstall, etc.).

```bash
# 1. Take backup of PostgreSQL if the node still has a live pod
#    (see Database backup above)

# 2. Provision new server and install k3s
#    (see Terraform in terraform/staging/)

# 3. Apply manifests in order (from k8s/DEPLOY.md):
kubectl apply -f k8s/staging/00-namespace.yaml
# Create secrets from template
kubectl apply -f k8s/staging/02-configmap.yaml
kubectl apply -f k8s/staging/rbac/
kubectl apply -f k8s/staging/postgres/
kubectl apply -f k8s/staging/redis/
kubectl apply -f k8s/staging/rabbitmq/
kubectl apply -f k8s/staging/minio/

# 4. Restore database from backup
#    (see Database restore above)

# 5. Create ghcr-pull-secret
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-username> \
  --docker-password=<PAT-with-read:packages> \
  -n virtual-closet-staging

# 6. Deploy application via CI
#    Trigger deploy-staging.yaml workflow manually or push to main
```

---

## Diagnosing with X-Request-ID

Every HTTP response from the backend and frontend includes an `X-Request-ID` header (UUID4). Use it to correlate logs across services.

```bash
# Extract request ID from a curl call
REQUEST_ID=$(curl -sI https://api.staging.virtualcloset.io/health \
  | grep -i x-request-id | awk '{print $2}' | tr -d '\r')
echo "Request ID: ${REQUEST_ID}"

# Search backend logs for that request
kubectl logs -l app=backend -n virtual-closet-staging --tail=1000 \
  | grep "${REQUEST_ID}"
```

Log format:
```
2026-06-18T21:00:00Z INFO core.middleware [550e8400-e29b-41d4-a716-446655440000] TokenRefresh skipped
2026-06-18T21:00:00Z INFO api.routers.auth [550e8400-e29b-41d4-a716-446655440000] Login attempt: user@example.com
```

Outside a request context (startup, background tasks), the request ID field shows `-`.

---

## Phase 2 observability (deferred)

Phase 1 (this bolt) uses `kubectl logs` + GitHub Actions health monitor + structured request IDs. Phase 2 should add:

| Component | Purpose |
|-----------|---------|
| **Promtail + Loki** | Log aggregation — ship pod stdout to Loki; query with LogQL |
| **Prometheus** | Metrics — scrape FastAPI `/metrics` (add `prometheus-fastapi-instrumentator`) |
| **Grafana** | Dashboards — request rate, error rate, latency, pod resource usage |
| **Jaeger** | Distributed tracing — propagate `X-Request-ID` as trace ID |
| **Alertmanager** | Route alerts to Slack/PagerDuty instead of GitHub Issues |
| **Automated DB backup** | Kubernetes CronJob running `pg_dump` + upload to object storage |

Trigger for Phase 2: staging environment is stable and serving real traffic; observability gaps cause actual incidents.
