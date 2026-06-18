# Infrastructure Operations Runbook

Terraform-managed k3s cluster on Hetzner. See [ADR-032](../memory-bank/bolts/037-infrastructure/adr-032-self-managed-k3s.md), [ADR-033](../memory-bank/bolts/037-infrastructure/adr-033-local-path-provisioner-non-ha-storage.md), [ADR-034](../memory-bank/bolts/037-infrastructure/adr-034-terraform-cloud-state-backend.md).

## Prerequisites

```bash
# Required tools
terraform --version   # >= 1.8.0 (use .terraform-version with tfenv)
kubectl version       # any recent version
ssh -V                # OpenSSH

# Install tfenv for version pinning (optional but recommended)
brew install tfenv    # macOS
tfenv install         # reads .terraform-version
```

## Initial Cluster Provisioning

```bash
cd infrastructure/environments/staging

# Authenticate with Terraform Cloud (one-time)
terraform login

# Initialize backend
terraform init

# Review the plan
TF_VAR_hcloud_token="$HCLOUD_TOKEN" \
TF_VAR_ssh_public_key="$(cat ~/.ssh/id_rsa.pub)" \
TF_VAR_admin_cidrs='["YOUR.IP/32"]' \
TF_VAR_object_storage_access_key="$OS_ACCESS_KEY" \
TF_VAR_object_storage_secret_key="$OS_SECRET_KEY" \
TF_VAR_postgres_password="$PG_PASSWORD" \
terraform plan

# Apply (creates all Hetzner resources + installs k3s)
# Estimated time: 5-10 minutes
terraform apply
```

After apply, retrieve the kubeconfig:

```bash
terraform output -raw kubeconfig > ~/.kube/staging-config
export KUBECONFIG=~/.kube/staging-config
kubectl get nodes
# Expected output:
# NAME                              STATUS   ROLES                  AGE
# virtualcloset-staging-control     Ready    control-plane,master   5m
# virtualcloset-staging-worker-1    Ready    <none>                 3m
```

## Adding a Worker Node

1. Increment worker count in `modules/cluster/main.tf` (use `count` on `hcloud_server.worker`)
2. `terraform plan` → verify only a new server is being added
3. `terraform apply`
4. New node auto-joins via k3s token; verify with `kubectl get nodes`

> Note: Existing PVs remain on their original node. Workloads using them will not migrate automatically. See ADR-033.

## Updating k3s Version

```bash
# 1. Change k3s_version in environments/staging/main.tf
# 2. Plan and review
terraform plan

# 3. Apply — this recreates nodes (destroy + create)
# ⚠ DATA LOSS RISK: take a manual backup before upgrading
# See: Backup & Restore → Manual Backup
terraform apply

# 4. Verify
kubectl get nodes
kubectl version
```

## Backup & Restore

### Verify Backup CronJob

```bash
# Check CronJob status
kubectl get cronjob postgres-backup

# List recent backup jobs
kubectl get jobs -l app=postgres-backup

# Trigger a manual backup immediately
kubectl create job --from=cronjob/postgres-backup manual-backup-$(date +%Y%m%d)

# Watch it run
kubectl logs -f job/manual-backup-$(date +%Y%m%d) -c backup
```

### List Backups in Object Storage

```bash
AWS_ACCESS_KEY_ID="$OS_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$OS_SECRET_KEY" \
aws s3 ls s3://virtualcloset-backups-staging/ \
  --endpoint-url https://fsn1.your-objectstorage.com \
  --recursive --human-readable --summarize
```

### Manual Backup

```bash
# Run pg_dump directly on the worker node
ssh root@<WORKER_PUBLIC_IP> \
  'PGPASSWORD=<pg_password> pg_dump -h localhost -U postgres virtual_closet | gzip > /tmp/manual_backup.sql.gz'

# Upload to Object Storage
scp root@<WORKER_PUBLIC_IP>:/tmp/manual_backup.sql.gz .
AWS_ACCESS_KEY_ID="$OS_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$OS_SECRET_KEY" \
aws s3 cp manual_backup.sql.gz s3://virtualcloset-backups-staging/ \
  --endpoint-url https://fsn1.your-objectstorage.com
```

### Restore from Backup

```bash
# 1. Download the backup file
AWS_ACCESS_KEY_ID="$OS_ACCESS_KEY" \
AWS_SECRET_ACCESS_KEY="$OS_SECRET_KEY" \
aws s3 cp s3://virtualcloset-backups-staging/backup_YYYYMMDD_HHMMSS.sql.gz . \
  --endpoint-url https://fsn1.your-objectstorage.com

# 2. Copy to worker node
scp backup_YYYYMMDD_HHMMSS.sql.gz root@<WORKER_PUBLIC_IP>:/tmp/

# 3. Restore into PostgreSQL
ssh root@<WORKER_PUBLIC_IP> << 'EOF'
  gunzip -c /tmp/backup_YYYYMMDD_HHMMSS.sql.gz | \
    PGPASSWORD=<pg_password> psql -h localhost -U postgres virtual_closet
  rm /tmp/backup_YYYYMMDD_HHMMSS.sql.gz
EOF

# 4. Verify row counts
kubectl exec -it deployment/fastapi -- python -c "
from core.database import engine
import asyncio, sqlalchemy as sa
async def check():
    async with engine.connect() as conn:
        result = await conn.execute(sa.text('SELECT COUNT(*) FROM mayoristas'))
        print('mayoristas:', result.scalar())
asyncio.run(check())
"
```

## Control Plane Recovery

If the CX21 control-plane fails (hardware fault, disk failure):

```bash
# 1. Destroy only the control-plane server
terraform destroy -target=module.cluster.hcloud_server.control_plane

# 2. Recreate it — k3s reinstalls with embedded etcd
terraform apply -target=module.cluster.hcloud_server.control_plane

# 3. Worker auto-rejoins (token is same)
# If worker needs to re-join manually:
ssh root@<WORKER_IP> systemctl restart k3s-agent

# 4. Retrieve new kubeconfig
terraform output -raw kubeconfig > ~/.kube/staging-config
kubectl get nodes
```

> Application data (PostgreSQL, MinIO) is on the **worker node** — it survives control-plane failure. Only cluster management (kubectl, new pod scheduling) is unavailable during recovery.

## Cluster Teardown

```bash
# ⚠ DESTRUCTIVE — deletes all Hetzner resources including data volumes
# Take a backup first!
terraform destroy
```

## Scaling the Cluster

The current worker node (CX31) provides:
- 2 vCPU, 8 GB RAM, 80 GB SSD

Expected resource usage per service (approximate):

| Service | CPU request | Memory request |
|---------|-------------|----------------|
| FastAPI | 200m | 512Mi |
| Celery worker | 500m | 512Mi |
| Frontend | 100m | 256Mi |
| PostgreSQL | 500m | 1Gi |
| Redis | 100m | 256Mi |
| RabbitMQ | 200m | 512Mi |
| MinIO | 200m | 512Mi |

If the CX31 becomes resource-constrained, scale by adding a second CX31 worker:
1. Add `count = 2` to `hcloud_server.worker` in `modules/cluster/main.tf`
2. `terraform apply` — new node joins cluster automatically
3. Re-evaluate storage: with 2 workers, Longhorn becomes viable (see ADR-033)

## Security Checklist

- [ ] `admin_cidrs` contains only current static IP addresses
- [ ] Hetzner API token scoped to project (not account-wide)
- [ ] SSH keys rotated when team members leave
- [ ] kubeconfig stored only in Terraform Cloud outputs and CI/CD secrets vault
- [ ] k8s Secrets (postgres-backup-credentials, object-storage-credentials) audited regularly
- [ ] Terraform Cloud 2FA enabled on organization account
