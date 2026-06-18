---
stage: technical-design
bolt: 039-kubernetes-config
created: 2026-06-18T11:30:00Z
---

## Technical Design: Kubernetes Deployment Configuration

---

### Files to Create (28 files)

```
k8s/
  staging/
    00-namespace.yaml
    01-secrets.yaml.template
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
      ingress.yaml
    rbac/
      serviceaccounts.yaml
      roles.yaml
      rolebindings.yaml
  .gitignore                        (excludes 01-secrets.yaml)
  DEPLOY.md
```

---

### 1. Cluster Prerequisites

These are one-time setup steps documented in `DEPLOY.md`, not managed by these manifests:

```bash
# 1. Install ingress-nginx (bare-metal/hostNetwork, see ADR-035)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/baremetal/deploy.yaml

# Patch controller to use hostNetwork on worker node
kubectl patch daemonset ingress-nginx-controller \
  -n ingress-nginx \
  --type=json \
  -p='[
    {"op":"add","path":"/spec/template/spec/hostNetwork","value":true},
    {"op":"add","path":"/spec/template/spec/nodeSelector","value":{"virtualcloset.io/role":"worker"}}
  ]'

# 2. Install cert-manager (TLS via Let's Encrypt)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml

# 3. Create namespace
kubectl apply -f k8s/staging/00-namespace.yaml

# 4. Create secrets from template (never commit actual secrets.yaml)
cp k8s/staging/01-secrets.yaml.template k8s/staging/01-secrets.yaml
# Edit 01-secrets.yaml with real values, then:
kubectl apply -f k8s/staging/01-secrets.yaml
rm k8s/staging/01-secrets.yaml  # remove after apply
```

---

### 2. Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: virtual-closet-staging
  labels:
    environment: staging
    app.kubernetes.io/managed-by: kubectl
```

---

### 3. Secrets Template (01-secrets.yaml.template)

`stringData` fields — k8s base64-encodes automatically. The template uses `REPLACE_*` placeholders; CI replaces them with `sed` or `envsubst` before `kubectl apply`.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: virtual-closet-secrets
  namespace: virtual-closet-staging
type: Opaque
stringData:
  POSTGRES_USER: "postgres"
  POSTGRES_PASSWORD: "REPLACE_PG_PASSWORD"
  DATABASE_URL: "postgresql+asyncpg://postgres:REPLACE_PG_PASSWORD@postgres:5432/virtual_closet"
  JWT_SECRET_KEY: "REPLACE_JWT_SECRET_KEY"
  TWO_FACTOR_ENCRYPTION_KEY: "REPLACE_2FA_KEY"
  MINIO_ROOT_USER: "REPLACE_MINIO_USER"
  MINIO_ROOT_PASSWORD: "REPLACE_MINIO_PASSWORD"
  MINIO_ACCESS_KEY: "REPLACE_MINIO_USER"
  MINIO_SECRET_KEY: "REPLACE_MINIO_PASSWORD"
  RABBITMQ_DEFAULT_USER: "REPLACE_RABBITMQ_USER"
  RABBITMQ_DEFAULT_PASS: "REPLACE_RABBITMQ_PASSWORD"
  REPLICATE_API_KEY: "REPLACE_REPLICATE_KEY"
  RESEND_API_KEY: "REPLACE_RESEND_KEY"
```

`k8s/staging/.gitignore` excludes `01-secrets.yaml` (the populated copy). Only the `.template` is committed.

---

### 4. ConfigMap

Non-sensitive values shared across backend + celery:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: virtual-closet-config
  namespace: virtual-closet-staging
data:
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRE_DAYS: "7"
  FRONTEND_URL: "https://staging.virtualcloset.io"
  BACKEND_URL: "https://api.staging.virtualcloset.io"
  MINIO_ENDPOINT: "http://minio:9000"
  MINIO_PUBLIC_ENDPOINT: "https://api.staging.virtualcloset.io/storage"
  MINIO_BUCKET_ORIGINALS: "originals"
  MINIO_BUCKET_GENERATED: "generated"
  MINIO_BUCKET_THUMBNAILS: "thumbnails"
  MINIO_BUCKET_MODEL_THUMBNAILS: "model-thumbnails"
  RABBITMQ_URL: "amqp://$(RABBITMQ_DEFAULT_USER):$(RABBITMQ_DEFAULT_PASS)@rabbitmq:5672/"
  REDIS_URL: "redis://redis:6379/0"
  VTON_PROVIDER: "replicate"
  COOKIE_SECURE: "true"
  SEED_IMGS_DIR: "/app/seed-imgs"
  FASHN_GARMENT_PHOTO_TYPE: "flat-lay"
  FASHN_LEG_POSTPROCESS: "true"
  FASHN_PRESERVE_LIMBS: "true"
```

Note: `RABBITMQ_URL` uses k8s dependent env var interpolation — `$(RABBITMQ_DEFAULT_USER)` resolves at pod startup from the Secret mounted as env. This is k8s native behavior when env vars reference other env vars in the same pod spec.

Actually, this interpolation is only supported within the same `env[]` list, not across ConfigMap and Secret. The cleaner approach: set RABBITMQ_URL directly in the pod's `env:` using valueFrom refs to compose the URL, or just put the full URL in the Secret (non-sensitive base URL in ConfigMap, credentials in Secret, compose in pod spec).

**Revised approach**: `RABBITMQ_URL` in the Secret:
```
RABBITMQ_URL: "amqp://REPLACE_RABBITMQ_USER:REPLACE_RABBITMQ_PASSWORD@rabbitmq:5672/"
```

---

### 5. Stateful Services Design

#### PostgreSQL StatefulSet

```yaml
# Key spec sections only
spec:
  replicas: 1
  selector:
    matchLabels: {app: postgres}
  serviceName: postgres
  template:
    spec:
      nodeSelector:
        virtualcloset.io/role: worker
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef: {name: virtual-closet-secrets, key: POSTGRES_USER}
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef: {name: virtual-closet-secrets, key: POSTGRES_PASSWORD}
            - name: POSTGRES_DB
              value: virtual_closet
          resources:
            requests: {cpu: 200m, memory: 256Mi}
            limits: {cpu: 500m, memory: 1Gi}
          startupProbe:
            exec:
              command: [pg_isready, -U, postgres]
            failureThreshold: 30
            periodSeconds: 5
          livenessProbe:
            exec:
              command: [pg_isready, -U, postgres]
            periodSeconds: 30
            timeoutSeconds: 5
          readinessProbe:
            exec:
              command: [pg_isready, -U, postgres]
            periodSeconds: 10
            timeoutSeconds: 5
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        storageClassName: local-path
        resources:
          requests:
            storage: 10Gi
```

**Service**: ClusterIP (headless — `clusterIP: None`) for stable StatefulSet DNS (`postgres-0.postgres.virtual-closet-staging.svc.cluster.local`). Backend uses `postgres` hostname, which resolves to the pod IP via the headless service.

#### MinIO StatefulSet

Notable difference from postgres: MinIO requires its own command:
```yaml
command: ["minio", "server", "/data", "--console-address", ":9001"]
```

Probes use MinIO's built-in health endpoints (no CLI probe needed):
```yaml
livenessProbe:
  httpGet: {path: /minio/health/live, port: 9000}
readinessProbe:
  httpGet: {path: /minio/health/ready, port: 9000}
```

#### RabbitMQ StatefulSet

```yaml
livenessProbe:
  exec:
    command: [rabbitmq-diagnostics, check_port_connectivity]
  periodSeconds: 30
  timeoutSeconds: 10
readinessProbe:
  tcpSocket:
    port: 5672
  periodSeconds: 10
```

Readiness uses TCP socket on AMQP port — simpler than HTTP management API (avoids credential issues in probe config).

---

### 6. Stateless Services Design

#### Backend Deployment

```yaml
spec:
  replicas: 2
  template:
    spec:
      serviceAccountName: backend
      containers:
        - name: backend
          image: virtual-closet/backend:IMAGE_TAG      # CI substitutes tag
          ports: [{containerPort: 8000}]
          envFrom:
            - configMapRef: {name: virtual-closet-config}
            - secretRef: {name: virtual-closet-secrets}
          resources:
            requests: {cpu: 200m, memory: 512Mi}
            limits: {cpu: 500m, memory: 1Gi}
          startupProbe:
            httpGet: {path: /health, port: 8000}
            failureThreshold: 24
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /health, port: 8000}
            periodSeconds: 30
            timeoutSeconds: 5
          readinessProbe:
            httpGet: {path: /health, port: 8000}
            periodSeconds: 10
            timeoutSeconds: 5
```

`IMAGE_TAG` is a placeholder replaced by CI (`sed -i "s/IMAGE_TAG/${GIT_SHA}/"` in bolt 040). The `.template` file uses `IMAGE_TAG`; the actual apply uses the substituted version.

#### Celery Deployment

Same image as backend; command overrides Dockerfile CMD:

```yaml
containers:
  - name: celery
    image: virtual-closet/backend:IMAGE_TAG
    command:
      - celery
      - -A
      - core.celery_app
      - worker
      - --loglevel=info
      - -Q
      - vton.generation.normal,vton.generation.priority,tryoff
    livenessProbe:
      exec:
        command:
          - sh
          - -c
          - celery inspect ping -d celery@$HOSTNAME -t 5 2>&1 | grep -q pong
      periodSeconds: 60
      timeoutSeconds: 10
      failureThreshold: 3
```

No readiness probe for Celery — it doesn't serve HTTP traffic.

#### Redis Deployment

```yaml
containers:
  - name: redis
    image: redis:7-alpine
    ports: [{containerPort: 6379}]
    resources:
      requests: {cpu: 50m, memory: 64Mi}
      limits: {cpu: 100m, memory: 128Mi}
    livenessProbe:
      exec:
        command: [redis-cli, ping]
      periodSeconds: 30
    readinessProbe:
      exec:
        command: [redis-cli, ping]
      periodSeconds: 10
```

No `nodeSelector` — Redis is stateless; any node is fine (only worker has no taint, so it will schedule there anyway).

#### Frontend Deployment

```yaml
spec:
  replicas: 2
  template:
    spec:
      serviceAccountName: frontend
      containers:
        - name: frontend
          image: virtual-closet/frontend:IMAGE_TAG
          ports: [{containerPort: 3000}]
          env:
            - name: NEXT_PUBLIC_API_URL
              valueFrom:
                configMapKeyRef: {name: virtual-closet-config, key: BACKEND_URL}
          resources:
            requests: {cpu: 50m, memory: 128Mi}
            limits: {cpu: 200m, memory: 256Mi}
          startupProbe:
            httpGet: {path: /api/health, port: 3000}
            failureThreshold: 12
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /api/health, port: 3000}
            periodSeconds: 30
          readinessProbe:
            httpGet: {path: /api/health, port: 3000}
            periodSeconds: 10
```

---

### 7. Ingress Design — Subdomain Routing

**Decision**: Two subdomains instead of path-prefix routing (see ADR-035 appendix):
- `staging.virtualcloset.io` → frontend:3000
- `api.staging.virtualcloset.io` → backend:8000

Path-prefix routing (`/api/*`) would require FastAPI to be mounted at `/api` prefix or nginx rewrite — more fragile. Subdomain routing requires zero app-level changes.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: virtual-closet-ingress
  namespace: virtual-closet-staging
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"    # file uploads
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - staging.virtualcloset.io
        - api.staging.virtualcloset.io
      secretName: virtual-closet-tls
  rules:
    - host: staging.virtualcloset.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port: {number: 3000}
    - host: api.staging.virtualcloset.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port: {number: 8000}
```

`proxy-body-size: 50m` — garment image uploads can be up to ~20MB; default nginx limit is 1MB.

---

### 8. RBAC Design

No workload needs k8s API access. RBAC provides identity isolation only.

```yaml
# serviceaccounts.yaml
ServiceAccount: frontend    (namespace: virtual-closet-staging)
ServiceAccount: backend     (namespace: virtual-closet-staging)
ServiceAccount: celery-worker (namespace: virtual-closet-staging)

# roles.yaml — empty role (no permissions granted)
Role: virtual-closet-role
rules: []    # explicit no-op; documents that no permissions are granted intentionally

# rolebindings.yaml — bind each SA to the empty role
RoleBinding: frontend-binding   → frontend SA
RoleBinding: backend-binding    → backend SA
RoleBinding: celery-binding     → celery-worker SA
```

Rationale for explicit empty Role: prevents accidental default ClusterRole inheritance and makes the intent clear to future reviewers.

---

### 9. ADRs to Create in Stage 3

| ADR | Decision | Tradeoff |
|-----|----------|----------|
| ADR-035 | ingress-nginx + hostNetwork DaemonSet on worker | Avoids Hetzner LB cost (~€5/mo); binds ports 80/443 directly on worker IP |
| ADR-036 | Redis as Deployment (no PVC) | Token denylist loss on restart → up to 7-day revocation gap; acceptable for staging |

---

### 10. Apply Order

```bash
# Cluster scope (once)
kubectl apply -f k8s/staging/00-namespace.yaml

# Secrets + config (before workloads)
kubectl apply -f k8s/staging/01-secrets.yaml    # populated from template
kubectl apply -f k8s/staging/02-configmap.yaml

# RBAC
kubectl apply -f k8s/staging/rbac/

# Infrastructure services first (stateful, slowest to start)
kubectl apply -f k8s/staging/postgres/
kubectl apply -f k8s/staging/redis/
kubectl apply -f k8s/staging/rabbitmq/
kubectl apply -f k8s/staging/minio/

# App services (depend on infra)
kubectl apply -f k8s/staging/backend/
kubectl apply -f k8s/staging/celery/
kubectl apply -f k8s/staging/frontend/

# Ingress last (routes must be available)
kubectl apply -f k8s/staging/ingress/
```

Alembic migrations run as a k8s Job before backend Deployment rollout — designed in bolt 041 (db-migrations).
