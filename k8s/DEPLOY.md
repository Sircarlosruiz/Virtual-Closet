# Kubernetes Deployment Guide: Staging

Full runbook for deploying Virtual Closet to the Hetzner k3s staging cluster provisioned in `infrastructure/`.

## DNS Prerequisites

Before deploying, create two A records pointing to the worker node's public IP:

```
staging.virtualcloset.io     → <WORKER_PUBLIC_IP>
api.staging.virtualcloset.io → <WORKER_PUBLIC_IP>
```

Get the worker IP from Terraform output:
```bash
cd infrastructure/environments/staging
terraform output worker_public_ip
```

## One-Time Cluster Setup

Run these once per cluster. They install cluster-wide components that are not managed by the `k8s/staging/` manifests.

### 1. Install ingress-nginx (bare-metal, ADR-035)

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/baremetal/deploy.yaml

# Patch to use hostNetwork on worker node (binds ports 80/443 directly)
kubectl patch daemonset ingress-nginx-controller \
  -n ingress-nginx \
  --type=json \
  -p='[
    {"op":"add","path":"/spec/template/spec/hostNetwork","value":true},
    {"op":"add","path":"/spec/template/spec/nodeSelector","value":{"virtualcloset.io/role":"worker"}}
  ]'

# Verify controller is running
kubectl -n ingress-nginx get pods -w
```

### 2. Install cert-manager (TLS via Let's Encrypt)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml

# Wait for webhook to be ready
kubectl -n cert-manager rollout status deployment/cert-manager-webhook

# Create ClusterIssuer for Let's Encrypt staging (use production issuer for production)
kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: carlosbustillo99@gmail.com
    privateKeySecretRef:
      name: letsencrypt-staging-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
EOF
```

## Deploy to Staging

### Step 1 — Create namespace

```bash
kubectl apply -f k8s/staging/00-namespace.yaml
```

### Step 2 — Create secrets

```bash
# Copy template and populate with real values
cp k8s/staging/01-secrets.yaml.template k8s/staging/01-secrets.yaml

# Edit the file — replace all REPLACE_* placeholders
# Then apply and immediately delete (never leave populated secrets on disk)
kubectl apply -f k8s/staging/01-secrets.yaml
rm k8s/staging/01-secrets.yaml
```

**In CI/CD**: use `envsubst` with secrets from the CI secrets vault (bolt 040 wires this up):
```bash
export REPLACE_PG_PASSWORD="$PG_PASSWORD"
export REPLACE_JWT_SECRET_KEY="$JWT_SECRET_KEY"
# ... etc
envsubst < k8s/staging/01-secrets.yaml.template | kubectl apply -f -
```

### Step 3 — Apply ConfigMap

```bash
kubectl apply -f k8s/staging/02-configmap.yaml
```

### Step 4 — Apply RBAC

```bash
kubectl apply -f k8s/staging/rbac/
```

### Step 5 — Deploy infrastructure services

```bash
kubectl apply -f k8s/staging/postgres/
kubectl apply -f k8s/staging/redis/
kubectl apply -f k8s/staging/rabbitmq/
kubectl apply -f k8s/staging/minio/

# Wait for all StatefulSets to be ready before deploying app services
kubectl -n virtual-closet-staging rollout status statefulset/postgres
kubectl -n virtual-closet-staging rollout status statefulset/rabbitmq
kubectl -n virtual-closet-staging rollout status statefulset/minio
```

### Step 6 — Run database migrations (bolt 041)

Before deploying the backend, run Alembic migrations as a k8s Job:
```bash
# See k8s/staging/migrations/ — created in bolt 041
kubectl apply -f k8s/staging/migrations/job.yaml
kubectl -n virtual-closet-staging wait --for=condition=complete job/alembic-migrate --timeout=120s
```

### Step 7 — Deploy application services

```bash
# Substitute IMAGE_TAG with the git SHA before applying
GIT_SHA=$(git rev-parse --short HEAD)

sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/backend/deployment.yaml | kubectl apply -f -
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/celery/deployment.yaml | kubectl apply -f -
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/frontend/deployment.yaml | kubectl apply -f -

kubectl apply -f k8s/staging/backend/service.yaml
kubectl apply -f k8s/staging/frontend/service.yaml

# Wait for rollout
kubectl -n virtual-closet-staging rollout status deployment/backend
kubectl -n virtual-closet-staging rollout status deployment/frontend
```

### Step 8 — Apply Ingress

```bash
kubectl apply -f k8s/staging/ingress/
```

## Verifying Deployment

```bash
# All pods running
kubectl -n virtual-closet-staging get pods

# Expected output (all Running):
# NAME                        READY   STATUS    RESTARTS
# postgres-0                  1/1     Running   0
# redis-xxxx                  1/1     Running   0
# rabbitmq-0                  1/1     Running   0
# minio-0                     1/1     Running   0
# backend-xxxx (x2)           1/1     Running   0
# celery-xxxx                 1/1     Running   0
# frontend-xxxx (x2)          1/1     Running   0

# Check health endpoints
curl https://api.staging.virtualcloset.io/health
# Expected: {"status":"ok"}

curl https://staging.virtualcloset.io/api/health
# Expected: {"status":"ok"}

# Verify TLS certificate issued
kubectl -n virtual-closet-staging get certificate virtual-closet-tls
```

## Post-Deploy: Create MinIO Buckets

MinIO starts empty. Create buckets before the backend can store files:

```bash
kubectl -n virtual-closet-staging exec -it statefulset/minio -- \
  mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

kubectl -n virtual-closet-staging exec -it statefulset/minio -- sh -c "
  mc mb local/originals
  mc mb local/generated
  mc mb local/thumbnails
  mc mb local/model-thumbnails
  mc anonymous set download local/generated
  mc anonymous set download local/thumbnails
"
```

## Rollback

```bash
# Roll back a deployment to the previous revision
kubectl -n virtual-closet-staging rollout undo deployment/backend
kubectl -n virtual-closet-staging rollout undo deployment/frontend

# Or roll back to a specific revision
kubectl -n virtual-closet-staging rollout history deployment/backend
kubectl -n virtual-closet-staging rollout undo deployment/backend --to-revision=2
```

## Resource Usage

See [infrastructure/OPERATIONS.md](../infrastructure/OPERATIONS.md) for node resource sizing and scaling guidance.

Current requests totals on worker CX31 (2 vCPU, 8 GB RAM):

| Metric | Used (requests) | Node capacity | Headroom |
|--------|-----------------|---------------|----------|
| CPU | ~1200m | 2000m | ~40% |
| Memory | ~1984Mi | 8192Mi | ~76% |
