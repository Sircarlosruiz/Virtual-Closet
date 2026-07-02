# Kubernetes Deployment Guide: Staging

Full runbook for deploying Virtual Closet to the AWS EKS staging cluster provisioned in `infrastructure/`.

## DNS Prerequisites

Before deploying, create two CNAME records pointing to the ingress Load Balancer:

```
staging.virtualcloset.io     → <INGRESS_LB_DNS>
api.staging.virtualcloset.io → <INGRESS_LB_DNS>
```

Get the ingress LB address after installing ingress-nginx:
```bash
kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## One-Time Cluster Setup

Run these once per cluster. They install cluster-wide components.

### 1. Configure kubeconfig

```bash
aws eks update-kubeconfig --region us-west-2 --name virtualcloset-staging
kubectl get nodes
```

### 2. Install ingress-nginx (LoadBalancer mode)

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"

# Verify controller is running
kubectl -n ingress-nginx get pods -w
```

### 3. Install cert-manager (TLS via Let's Encrypt)

```bash
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --repo https://charts.jetstack.io \
  --set installCRDs=true

# Wait for webhook to be ready
kubectl -n cert-manager rollout status deployment/cert-manager-webhook

# Create ClusterIssuer for Let's Encrypt staging
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
cp k8s/staging/01-secrets.yaml.template k8s/staging/01-secrets.yaml
# Edit the file — replace all REPLACE_* placeholders
kubectl apply -f k8s/staging/01-secrets.yaml
rm k8s/staging/01-secrets.yaml
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

kubectl -n virtual-closet-staging rollout status statefulset/postgres
kubectl -n virtual-closet-staging rollout status statefulset/rabbitmq
kubectl -n virtual-closet-staging rollout status statefulset/minio
```

### Step 6 — Run database migrations

```bash
GIT_SHA=$(git rev-parse --short HEAD)
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/migrations/job.yaml | kubectl apply -f -
kubectl -n virtual-closet-staging wait --for=condition=complete job/alembic-migrate-${GIT_SHA} --timeout=300s
```

### Step 7 — Deploy application services

```bash
GIT_SHA=$(git rev-parse --short HEAD)

sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/backend/deployment.yaml | kubectl apply -f -
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/celery/deployment.yaml | kubectl apply -f -
sed "s/IMAGE_TAG/${GIT_SHA}/g" k8s/staging/frontend/deployment.yaml | kubectl apply -f -

kubectl apply -f k8s/staging/backend/service.yaml
kubectl apply -f k8s/staging/frontend/service.yaml

kubectl -n virtual-closet-staging rollout status deployment/backend
kubectl -n virtual-closet-staging rollout status deployment/frontend
```

### Step 8 — Apply Ingress

```bash
kubectl apply -f k8s/staging/ingress/
```

## Verifying Deployment

```bash
kubectl -n virtual-closet-staging get pods

curl https://api.staging.virtualcloset.io/health
curl https://staging.virtualcloset.io/api/health
```

## Post-Deploy: Create MinIO Buckets

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
kubectl -n virtual-closet-staging rollout undo deployment/backend
kubectl -n virtual-closet-staging rollout undo deployment/frontend
```

## Resource Usage

Current requests totals across 2x t3.large nodes (2 vCPU, 8 GB RAM each):

| Metric | Used (requests) | Cluster capacity | Headroom |
|--------|-----------------|------------------|----------|
| CPU | ~1200m | 4000m | ~70% |
| Memory | ~1984Mi | 16384Mi | ~88% |
