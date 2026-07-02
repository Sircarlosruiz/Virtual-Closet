# Infrastructure Operations Runbook

Terraform-managed EKS cluster on AWS. Region: `us-west-2` (Oregon).

## Prerequisites

```bash
# Required tools
terraform --version   # >= 1.8.0
aws --version         # AWS CLI v2
kubectl version       # any recent version
helm version          # >= 3.0

# Configure AWS credentials
aws configure
# Or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
```

## Initial Cluster Provisioning

```bash
cd infrastructure/environments/staging

terraform init

TF_VAR_admin_cidrs='["YOUR.IP/32"]' \
TF_VAR_postgres_password="$PG_PASSWORD" \
terraform plan

# Apply (creates VPC, EKS cluster, node group, S3 backup bucket)
# Estimated time: 15-20 minutes
terraform apply
```

After apply, configure kubeconfig:

```bash
aws eks update-kubeconfig --region us-west-2 --name virtualcloset-staging
kubectl get nodes
# Expected output:
# NAME                                       STATUS   ROLES    AGE
# ip-10-0-10-xx.us-west-2.compute.internal   Ready    <none>   5m
# ip-10-0-11-xx.us-west-2.compute.internal   Ready    <none>   5m
```

## Scaling the Node Group

```bash
# Increase desired capacity
terraform apply -var="node_desired_size=3"

# Or set min/max for auto-scaling
terraform apply -var="node_min_size=2" -var="node_max_size=5"
```

> EBS volumes are attached to specific nodes. StatefulSet PVCs remain on their original node.

## Updating Kubernetes Version

```bash
# 1. Change eks_kubernetes_version in environments/staging/main.tf
# 2. Plan and review
terraform plan

# 3. Apply — EKS performs a rolling update of the control plane
# ⚠ Take a manual backup before upgrading
terraform apply

# 4. Update node group (rolling replacement)
terraform apply

# 5. Verify
kubectl get nodes
kubectl version
```

## Backup & Restore

### Verify Backup CronJob

```bash
kubectl get cronjob postgres-backup -n virtual-closet-staging
kubectl create job --from=cronjob/postgres-backup manual-backup-$(date +%Y%m%d) \
  -n virtual-closet-staging
kubectl logs -f job/manual-backup-$(date +%Y%m%d) -c backup \
  -n virtual-closet-staging
```

### List Backups in S3

```bash
aws s3 ls s3://virtualcloset-staging-backups-staging/ \
  --recursive --human-readable --summarize
```

### Restore from Backup

```bash
# 1. Download the backup file
aws s3 cp s3://virtualcloset-staging-backups-staging/backup_YYYYMMDD_HHMMSS.sql.gz .

# 2. Decompress
gunzip backup_YYYYMMDD_HHMMSS.sql.gz

# 3. Restore into PostgreSQL via kubectl exec
kubectl exec -i postgres-0 -n virtual-closet-staging -- \
  psql -U postgres virtual_closet < backup_YYYYMMDD_HHMMSS.sql

# 4. Verify
kubectl exec postgres-0 -n virtual-closet-staging -- \
  psql -U postgres virtual_closet -c "SELECT COUNT(*) FROM mayoristas;"
```

## Cluster Teardown

```bash
# ⚠ DESTRUCTIVE — deletes all AWS resources including EBS volumes and S3 bucket
# Take a backup first!
terraform destroy
```

## Security Checklist

- [ ] `admin_cidrs` contains only current static IP addresses
- [ ] AWS credentials scoped with minimal IAM permissions
- [ ] SSH keys rotated when team members leave
- [ ] kubeconfig generated via `aws eks update-kubeconfig` (IAM-based, no static tokens)
- [ ] S3 bucket encryption enabled (KMS)
- [ ] S3 bucket public access blocked
- [ ] EKS cluster endpoint public access restricted to admin CIDRs
