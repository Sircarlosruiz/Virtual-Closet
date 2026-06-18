# Database Migrations

Virtual Closet uses [Alembic](https://alembic.sqlalchemy.org/) with an async SQLAlchemy engine to manage PostgreSQL schema changes.

## Authoring a migration

```bash
# Generate a migration from ORM model changes (preferred)
cd backend
alembic revision --autogenerate -m "add_user_preferences_table"

# Generate a blank migration for manual DDL
alembic revision -m "create_index_on_garments_owner"
```

After generation, **always review the generated file** before committing:

- Verify the auto-detected changes match your intent
- Add any missing index creation or constraint changes
- Ensure `downgrade()` is complete and correct — never remove it

Migration files live in `backend/alembic/versions/`. Commit them alongside the model changes that triggered them.

---

## Zero-downtime rules

During a Kubernetes deployment, the migration Job runs **before** the new backend pods start, but the **old backend pods are still serving traffic**. Every migration must leave the schema compatible with the old code.

### Allowed (safe while old pods run)

| Change | Notes |
|--------|-------|
| Add nullable column | Old code ignores it; new code reads `None` default |
| Add column with DEFAULT | Old inserts use the DB default |
| Add new table | Old code ignores unknown tables |
| Add index | Transparent to app layer |
| Widen column type | e.g., VARCHAR(50) → VARCHAR(255) |

### Not allowed (breaks old pods)

| Change | Why | Safe alternative |
|--------|-----|-----------------|
| Rename column | Old code references old name | 2-phase: add new → dual-write → drop old (separate deploy) |
| Drop column old code uses | Old code breaks on SELECT | 2-phase: stop reading in code → drop column (separate deploy) |
| Add NOT NULL without DEFAULT | Old inserts fail | Add as nullable first; backfill; add NOT NULL constraint in separate deploy |
| Change column type incompatibly | Old reads may fail type coercion | 2-phase: add new column → migrate data → remove old |
| Rename table | Old code breaks | 2-phase with view shim |

### 2-phase pattern for breaking changes

**Phase 1** (this deploy): additive migration + code that handles both old and new shape.  
**Phase 2** (next deploy, after all old pods are retired): cleanup migration that removes the old shape.

---

## Running migrations locally

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Check current revision
docker compose exec backend alembic current

# Show pending migrations
docker compose exec backend alembic history --indicate-current

# Downgrade one step
docker compose exec backend alembic downgrade -1
```

---

## Running migrations on staging (manual / out-of-band)

Normally migrations run automatically via CI (see CI/CD pipeline). For manual execution:

```bash
export GIT_SHA=<7-char git sha>
export NS=virtual-closet-staging

# Delete previous Job for this SHA if it exists (Jobs are immutable)
kubectl delete job alembic-migrate-${GIT_SHA} -n ${NS} --ignore-not-found

# Submit migration Job
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/migrations/job.yaml \
  | kubectl create -f -

# Stream logs
kubectl logs -f job/alembic-migrate-${GIT_SHA} -n ${NS}

# Confirm success
kubectl wait --for=condition=complete \
  job/alembic-migrate-${GIT_SHA} -n ${NS} --timeout=300s
```

---

## Rollback procedure

> Use rollback only when the migration caused a production issue. Coordinate with the team before rolling back — rolling back schema changes while new code is deployed can cause data loss.

```bash
export GIT_SHA=<sha that applied the bad migration>
export PREVIOUS_SHA=<sha to roll back to>
export NS=virtual-closet-staging

# 1. Scale backend to zero (stops writes using new schema)
kubectl scale deployment/backend --replicas=0 -n ${NS}

# 2. Apply rollback Job (uses the NEW image — it contains the downgrade() function)
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/migrations/rollback-job.yaml.template \
  | kubectl create -f -

# 3. Wait for rollback to complete
kubectl wait --for=condition=complete \
  job/alembic-rollback-${GIT_SHA} -n ${NS} --timeout=120s

# 4. Verify schema is at expected revision
kubectl run alembic-check --rm -it --restart=Never \
  --image=virtual-closet/backend:${PREVIOUS_SHA} \
  --env-from=configmap/virtual-closet-config \
  --env-from=secret/virtual-closet-secrets \
  -- alembic current

# 5. Re-deploy the previous image
sed "s/IMAGE_TAG/${PREVIOUS_SHA}/g" k8s/staging/backend/deployment.yaml \
  | kubectl apply -f -
sed "s/IMAGE_TAG/${PREVIOUS_SHA}/g" k8s/staging/celery/deployment.yaml \
  | kubectl apply -f -

# 6. Scale backend back up
kubectl scale deployment/backend --replicas=2 -n ${NS}
```

---

## Troubleshooting

### Job stuck in Pending

```bash
kubectl describe job/alembic-migrate-${GIT_SHA} -n virtual-closet-staging
kubectl describe pod -l app.kubernetes.io/name=alembic-migrate -n virtual-closet-staging
```

Common causes: image pull failure (check `imagePullPolicy`, registry credentials), resource quota exceeded, node not schedulable.

### Job failed — "connection refused" or timeout

PostgreSQL is not ready. Check:

```bash
kubectl get pods -n virtual-closet-staging -l app.kubernetes.io/name=postgres
kubectl exec postgres-0 -n virtual-closet-staging -- pg_isready -U postgres
```

Wait for PostgreSQL to pass its readiness probe, then re-submit the migration Job.

### Job failed — "column already exists" or "relation already exists"

A previous migration attempt partially completed non-transactional DDL (e.g., `CREATE INDEX CONCURRENTLY`). Do NOT re-run the Job — it will fail again.

Steps:
1. `kubectl logs job/alembic-migrate-${GIT_SHA} -n virtual-closet-staging` — identify which statement failed
2. Connect to the DB and confirm whether the object exists: `\d+ <table_name>`, `\di+ <index_name>`
3. If the object exists and is correct: manually stamp the revision as applied:
   ```bash
   kubectl run alembic-stamp --rm -it --restart=Never \
     --image=virtual-closet/backend:${GIT_SHA} \
     --env-from=configmap/virtual-closet-config \
     --env-from=secret/virtual-closet-secrets \
     -- alembic stamp <revision_id>
   ```
4. Re-submit the migration Job — it will see the revision already applied and move to the next one.

### Alembic lock table / "Can't locate revision"

```bash
# Check alembic_version table
kubectl exec postgres-0 -n virtual-closet-staging -- \
  psql -U postgres -d virtualcloset -c "SELECT * FROM alembic_version;"
```

If the table shows an unknown revision ID (e.g., from a branch that was rebased), manually update it:
```bash
# Correct the stored revision to a known good revision
alembic stamp <known_revision_id>
```

### Revision conflict (two heads)

```bash
alembic heads  # shows multiple heads
alembic merge heads -m "merge_branch_migrations"
```

Commit the merge revision before deploying.
