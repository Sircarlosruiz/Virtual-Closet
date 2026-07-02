# CI/CD Pipeline

Virtual Closet uses GitHub Actions for automated build, test, and deployment to staging on AWS EKS.

## Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| PR | `.github/workflows/pr.yaml` | `pull_request → main` | Build + test; no image push |
| Deploy Staging | `.github/workflows/deploy-staging.yaml` | `push → main` | Build + push + migrate + deploy |
| Rollback Staging | `.github/workflows/rollback-staging.yaml` | `workflow_dispatch` | Manual rollback |

## One-time setup

### 1. Create the GitHub Environment

In the repo settings: **Settings → Environments → New environment → `staging`**

Set the environment URL to `https://staging.virtualcloset.io`.

---

### 2. Add GitHub secrets

| Secret | Scope | Value |
|--------|-------|-------|
| `AWS_ACCESS_KEY_ID` | `staging` environment | IAM access key for CI deployer |
| `AWS_SECRET_ACCESS_KEY` | `staging` environment | IAM secret key for CI deployer |
| `AWS_REGION` | `staging` environment | `us-west-2` |

All other deployment secrets (DB passwords, JWT keys, etc.) live in `k8s/staging/01-secrets.yaml` applied directly to the cluster — not in GitHub.

#### Creating the CI IAM User

```bash
# Create IAM user for CI
aws iam create-user --user-name virtualcloset-ci

# Attach EKS + ECR policy
aws iam attach-user-policy \
  --user-name virtualcloset-ci \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CLUSTER_POLICY

# Create access keys
aws iam create-access-key --user-name virtualcloset-ci
# Save the AccessKeyId and SecretAccessKey as GitHub secrets
```

Alternatively, use a more restrictive inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:PutImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 3. Create the `ghcr-pull-secret` on the cluster

EKS nodes need credentials to pull from ghcr.io (private packages):

```bash
# Create a GitHub PAT with read:packages scope at github.com/settings/tokens
# Then from your local machine (with kubeconfig configured):
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<PAT-with-read:packages> \
  -n virtual-closet-staging
```

This secret is referenced by `imagePullSecrets` in all Deployment and Job specs.

---

### 4. Set branch protection rules

In **Settings → Branches → Add branch protection rule** for `main`:

- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Required checks: `backend-ci`, `frontend-ci`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

---

## Deploy pipeline details

### Job graph (deploy-staging.yaml)

```
backend-ci ──┐
             ├── push-images ──── deploy
frontend-ci ─┘
```

### Migration gate

The `deploy` job runs the Alembic migration Job BEFORE updating any Deployment. If the migration fails or times out, the workflow halts — no pods are updated with the new image. See [MIGRATIONS.md](MIGRATIONS.md) for rollback procedure.

### Image naming

| Service | Image |
|---------|-------|
| Backend | `ghcr.io/{owner}/backend:staging-{sha7}` |
| Frontend | `ghcr.io/{owner}/frontend:staging-{sha7}` |

`{owner}` is the GitHub repository owner (`github.repository_owner`). Tags are immutable per SHA. `staging-latest` is a moving pointer used only for Docker layer caching.

### Health check gate

After pods reach `Ready`, the pipeline curls both public endpoints up to 12 times with 10s between attempts (120s total):

- `https://api.staging.virtualcloset.io/health` → HTTP 200
- `https://staging.virtualcloset.io/api/health` → HTTP 200 `{"status":"ok"}`

If either check fails after 120s, the workflow exits non-zero and the last 50 lines of backend pod logs are printed.

---

## Manual rollback

Use the **Rollback Staging** workflow via GitHub UI:

**Actions → Rollback Staging → Run workflow**

| Input | Value |
|-------|-------|
| `image_sha` | 7-char SHA of the image that applied the bad migration |
| `target_sha` | 7-char SHA of the previous good image |

The workflow:
1. Scales backend to 0 replicas
2. Runs `alembic downgrade -1` using the bad image (it contains the `downgrade()` function)
3. Redeploys the previous image for all services
4. Validates health checks

See [MIGRATIONS.md](MIGRATIONS.md) for the full manual procedure.

---

## Rotating AWS credentials

Rotate quarterly or immediately on team member departure:

```bash
# Delete old access key
aws iam delete-access-key \
  --user-name virtualcloset-ci \
  --access-key-id <OLD_KEY_ID>

# Create new access key
aws iam create-access-key --user-name virtualcloset-ci
# Update GitHub secrets AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

---

## Troubleshooting

### `push-images` fails — "denied: permission_denied"

The `packages: write` permission is set on the `push-images` job. Check that the GitHub repository has **Packages write** permission granted to Actions under **Settings → Actions → General → Workflow permissions**.

### `deploy` fails — "Unable to connect to the server"

AWS credentials are expired or the EKS cluster endpoint has changed. Verify with:

```bash
aws eks describe-cluster --name virtualcloset-staging --region us-west-2 \
  --query 'cluster.endpoint'
```

### `deploy` fails — migration job timeout

The Alembic migration job exceeded 300s. Check PostgreSQL availability:

```bash
kubectl exec postgres-0 -n virtual-closet-staging -- pg_isready -U postgres
kubectl logs -l app.kubernetes.io/name=alembic-migrate -n virtual-closet-staging
```

### Backend `rollout status` times out

Pods are not reaching `Ready`. Check:

```bash
kubectl get pods -n virtual-closet-staging
kubectl describe pod <pod-name> -n virtual-closet-staging
kubectl logs <pod-name> -n virtual-closet-staging
```

Common causes: image pull failure (`ghcr-pull-secret` missing or expired), startup probe failures, missing env vars in k8s Secret.

### `pnpm build` fails in CI — "Cannot find module"

The frontend build runs with placeholder env vars. If a module requires a real API at build time, add a `NEXT_PUBLIC_*` env var to the `frontend-ci` → `Build (type check)` step's `env` block in the workflow.
