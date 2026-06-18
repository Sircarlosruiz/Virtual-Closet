---
stage: domain-model
bolt: 039-kubernetes-config
created: 2026-06-18T11:00:00Z
---

## Domain Model: Kubernetes Deployment Configuration

---

### Cluster Context (from bolt 037)

| Property | Value |
|----------|-------|
| Distribution | k3s on Hetzner |
| Control plane | CX21 — NoSchedule taint (no workloads) |
| Worker | CX31 — 2 vCPU, 8 GB RAM, 80 GB SSD |
| Storage provisioner | `local-path` (k3s built-in, node-local) |
| Ingress controller | None pre-installed (traefik disabled at install) |
| Node labels | `virtualcloset.io/role=worker`, `virtualcloset.io/workload=stateful` |
| Namespace | `virtual-closet-staging` |

---

### Service Inventory

| Service | k8s Kind | PVC | Port | Image |
|---------|----------|-----|------|-------|
| frontend | Deployment | ✗ | 3000 | `virtual-closet/frontend:{tag}` |
| backend (FastAPI) | Deployment | ✗ | 8000 | `virtual-closet/backend:{tag}` |
| celery_worker | Deployment | ✗ | — | `virtual-closet/backend:{tag}` (same image, different CMD) |
| postgres | StatefulSet | ✅ 10 Gi | 5432 | `postgres:16-alpine` |
| redis | Deployment | ✗ | 6379 | `redis:7-alpine` |
| minio | StatefulSet | ✅ 20 Gi | 9000 / 9001 | `minio/minio:latest` |
| rabbitmq | StatefulSet | ✅ 5 Gi | 5672 / 15672 | `rabbitmq:3.12-management` |

**Redis as Deployment (no PVC)**: Sessions use JWT tokens (stateless auth), Redis holds the token denylist + rate-limit counters. Loss on pod restart means users with revoked tokens may temporarily regain access until token expiry (max 7 days). Acceptable for staging; production may warrant StatefulSet. → ADR-036.

---

### Entities

#### `Namespace`

```
name: virtual-closet-staging
labels:
  app.kubernetes.io/managed-by: kubectl
  environment: staging
```

Single namespace for all staging services. RBAC is scoped to this namespace.

---

#### `Workload`

Abstract base — either `Deployment` (stateless) or `StatefulSet` (stateful).

| Attribute | Type | Notes |
|-----------|------|-------|
| `name` | string | kebab-case; matches service name |
| `replicas` | int | stateless: 1–2; stateful: 1 (local-path PVs are node-local) |
| `image` | `ImageRef` | `{registry}/{service}:{tag}` |
| `command` | string[] | overrides Dockerfile CMD only for celery |
| `env_from` | `EnvSource[]` | references to ConfigMap + Secret |
| `resources` | `ResourceRequirements` | requests + limits |
| `probes` | `ProbeSet` | liveness + readiness + startup |
| `node_selector` | map | StatefulSets: `virtualcloset.io/role: worker` (PV locality) |
| `service_account` | string | dedicated SA per workload |

**Stateful services MUST** set `nodeSelector: virtualcloset.io/role: worker` — local-path PVs are created on the node where the pod first schedules; moving the pod to another node loses the data.

---

#### `StatefulSet` extends Workload

| Attribute | Type | Notes |
|-----------|------|-------|
| `volume_claim_templates` | `PVCTemplate[]` | declares storage per replica |
| `service_name` | string | headless Service name for stable DNS |
| `pod_management_policy` | `Parallel \| OrderedReady` | `OrderedReady` for postgres (safe startup) |

---

#### `PersistentVolumeClaim`

| Service | Size | Access mode | Storage class |
|---------|------|-------------|---------------|
| postgres | 10 Gi | ReadWriteOnce | local-path |
| minio | 20 Gi | ReadWriteOnce | local-path |
| rabbitmq | 5 Gi | ReadWriteOnce | local-path |

`ReadWriteOnce` — only one pod can mount; enforced by local-path provisioner.

---

#### `Service`

| Service | Type | Ports | Notes |
|---------|------|-------|-------|
| frontend | ClusterIP | 3000 | Exposed via Ingress |
| backend | ClusterIP | 8000 | Exposed via Ingress at `/api/*` |
| postgres | ClusterIP (headless) | 5432 | Headless for stable StatefulSet DNS |
| redis | ClusterIP | 6379 | Internal only |
| minio | ClusterIP | 9000, 9001 | 9001 = console (internal dev only) |
| rabbitmq | ClusterIP | 5672, 15672 | 15672 = management (internal dev only) |
| celery | None | — | No Service; worker only consumes RabbitMQ |

---

#### `Ingress`

Routing via `ingress-nginx` controller (→ ADR-035):

| Path | Backend Service | Notes |
|------|-----------------|-------|
| `/api/*` | `backend:8000` | All API routes; strip `/api` prefix |
| `/*` | `frontend:3000` | Catch-all; Next.js handles routing |

TLS: cert-manager + Let's Encrypt for staging domain. `staging.virtualcloset.io` → worker public IP.

---

#### `ConfigMap`

Non-secret configuration shared across backend + celery.

**`virtual-closet-config`** (backend + celery share this):

| Key | Value (staging) | Notes |
|-----|-----------------|-------|
| `JWT_ALGORITHM` | `HS256` | Non-sensitive |
| `JWT_EXPIRE_DAYS` | `7` | Non-sensitive |
| `FRONTEND_URL` | `https://staging.virtualcloset.io` | Must be real domain |
| `BACKEND_URL` | `https://staging.virtualcloset.io/api` | Via Ingress |
| `MINIO_ENDPOINT` | `http://minio:9000` | Internal k8s DNS |
| `MINIO_PUBLIC_ENDPOINT` | `https://staging.virtualcloset.io/storage` | Or direct MinIO URL |
| `MINIO_BUCKET_*` | `originals`, `generated`, `thumbnails`, `model-thumbnails` | Bucket names |
| `RABBITMQ_URL` | `amqp://rabbitmq:5672/` (user/pass from Secret) | Base URL; credentials injected separately |
| `REDIS_URL` | `redis://redis:6379/0` | Non-sensitive |
| `VTON_PROVIDER` | `replicate` | Production uses Replicate API |
| `COOKIE_SECURE` | `true` | HTTPS in staging |
| `SEED_IMGS_DIR` | `/app/seed-imgs` | Same path as Dockerfile |

---

#### `Secret`

Sensitive values. Template committed; actual values injected at deploy time by CI/CD.

**`virtual-closet-secrets`** (opaque):

| Key | Source |
|-----|--------|
| `DATABASE_URL` | postgresql+asyncpg://postgres:{PG_PASSWORD}@postgres:5432/virtual_closet |
| `POSTGRES_PASSWORD` | Used by postgres StatefulSet |
| `JWT_SECRET_KEY` | Random 64-char hex string |
| `TWO_FACTOR_ENCRYPTION_KEY` | Fernet key |
| `MINIO_ROOT_USER` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | MinIO admin password |
| `MINIO_ACCESS_KEY` | Same as MINIO_ROOT_USER (MinIO default) |
| `MINIO_SECRET_KEY` | Same as MINIO_ROOT_PASSWORD |
| `RABBITMQ_DEFAULT_USER` | RabbitMQ admin username |
| `RABBITMQ_DEFAULT_PASS` | RabbitMQ admin password |
| `REPLICATE_API_KEY` | Replicate.com token |
| `RESEND_API_KEY` | Email delivery token |

---

#### `ProbeSet`

Three probe types per workload:

| Probe | Question | Action on failure |
|-------|----------|-------------------|
| `startup` | Is the app still booting? | Pause liveness/readiness checks |
| `liveness` | Is the process alive? | Restart pod |
| `readiness` | Can this pod receive traffic? | Remove from Service endpoints |

**Liveness MUST NOT check external dependencies** — a database outage should not restart the app pod; the app pod is alive, just waiting. Readiness may check dependencies.

---

#### `ProbeConfig` — per service

| Service | Liveness | Readiness | Startup |
|---------|----------|-----------|---------|
| frontend | HTTP GET `/api/health` | HTTP GET `/api/health` | failureThreshold=12, periodSeconds=5 (60s max) |
| backend | HTTP GET `/health` | HTTP GET `/health` | failureThreshold=24, periodSeconds=5 (2min max) |
| celery | exec `celery inspect ping` | exec `celery inspect ping` | failureThreshold=24, periodSeconds=5 |
| postgres | exec `pg_isready -U postgres` | exec `pg_isready -U postgres` | failureThreshold=30, periodSeconds=5 |
| redis | exec `redis-cli ping` | exec `redis-cli ping` | failureThreshold=12, periodSeconds=5 |
| minio | HTTP GET `/minio/health/live` | HTTP GET `/minio/health/ready` | failureThreshold=12, periodSeconds=5 |
| rabbitmq | exec `rabbitmq-diagnostics check_port_connectivity` | HTTP GET `/api/health` (management:15672) | failureThreshold=24, periodSeconds=5 |

**Startup probes** prevent liveness killing a slow-starting pod. Once startup succeeds, liveness takes over.

---

#### `ResourceRequirements`

Target: single CX31 worker (2 vCPU, 8 GB RAM). All workloads must fit with headroom.

| Service | CPU request | CPU limit | Mem request | Mem limit |
|---------|-------------|-----------|-------------|-----------|
| frontend | 50m | 200m | 128Mi | 256Mi |
| backend | 200m | 500m | 512Mi | 1Gi |
| celery | 500m | 1000m | 512Mi | 1.5Gi |
| postgres | 200m | 500m | 256Mi | 1Gi |
| redis | 50m | 100m | 64Mi | 128Mi |
| minio | 100m | 200m | 256Mi | 512Mi |
| rabbitmq | 100m | 200m | 256Mi | 512Mi |
| **Total requests** | **1200m** (60%) | **2700m** | **1984Mi** (49%) | **4864Mi** |

Conservative initial sizing. 40% CPU and 51% memory headroom for bursts.

---

#### `ServiceAccount` + RBAC

Each workload gets a dedicated ServiceAccount. No workload needs k8s API access, so no ClusterRole is needed.

| SA name | Used by | Permissions |
|---------|---------|-------------|
| `frontend` | frontend Deployment | None (default k8s SA permissions only) |
| `backend` | backend Deployment | None |
| `celery-worker` | celery Deployment | None |
| Stateful services | postgres, redis, minio, rabbitmq | Default SA (no dedicated SA needed) |

The `default` SA in the namespace has no explicit permissions beyond the k8s baseline.

---

### Manifest Directory Structure

```
k8s/
  staging/
    00-namespace.yaml
    01-secrets.yaml.template        # committed; CI substitutes values
    02-configmap.yaml
    postgres/
      statefulset.yaml
      service.yaml
    redis/
      deployment.yaml
      service.yaml
    rabbitmq/
      statefulset.yaml
      service.yaml
    minio/
      statefulset.yaml
      service.yaml
    backend/
      deployment.yaml
      service.yaml
    celery/
      deployment.yaml
    frontend/
      deployment.yaml
      service.yaml
    ingress/
      ingress.yaml                  # routing rules
    rbac/
      serviceaccounts.yaml
      roles.yaml
      rolebindings.yaml
```

**Naming convention**: `00-` / `01-` / `02-` prefix on cluster-scoped resources ensures they apply before namespace-scoped resources in `kubectl apply -f`.

---

### Domain Rules

1. **All stateful StatefulSets MUST have `nodeSelector: virtualcloset.io/role: worker`** — local-path PVs are node-local; rescheduling to a different node loses data permanently.
2. **All pods MUST have `resources.requests` set** — without requests, the scheduler can't make placement decisions; workloads may OOM-kill the node.
3. **All pods MUST have `resources.limits` set** — prevents a runaway pod from starving other services on the single worker node.
4. **Liveness probes MUST be self-contained** — no external HTTP calls; exec or localhost-only probes only.
5. **Secrets file MUST NOT contain real values** — `.yaml.template` extension; `secrets.yaml` (no template suffix) is gitignored.
6. **`replicas > 1` ONLY for stateless services** — frontend: 2, backend: 2, celery: 1 (GPU task queue; parallel workers share queue but not GPU).
7. **StatefulSets: `replicas: 1`** — local-path PVs cannot be shared across replicas (ReadWriteOnce).

---

### Relationships

```
Namespace
  └── ConfigMap (virtual-closet-config)
  └── Secret (virtual-closet-secrets)
  └── ServiceAccount[] (frontend, backend, celery-worker)
  └── Role / RoleBinding[]
  └── Deployment[] (frontend, backend, celery, redis)
       └── PodSpec
            ├── envFrom: [ConfigMap, Secret]
            ├── resources: ResourceRequirements
            └── probes: ProbeSet
  └── StatefulSet[] (postgres, minio, rabbitmq)
       ├── volumeClaimTemplates: PVCTemplate[]
       └── PodSpec (same as Deployment)
  └── Service[] (per workload except celery)
  └── Ingress (routes → frontend, backend)
```
