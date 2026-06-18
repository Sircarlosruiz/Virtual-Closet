---
stage: technical-design
bolt: 037-infrastructure
created: 2026-06-17T17:15:00Z
---

## Technical Design: infrastructure-provisioning

---

### Architecture Pattern

**Selected Pattern**: Modular Terraform with Remote State + hcloud Provider

Infrastructure is expressed as composable Terraform modules. Each module encapsulates one infrastructure concern. Modules are composed by a root `main.tf` that wires them together. Remote state lives in Hetzner Object Storage (S3-compatible endpoint) with Terraform Cloud as the preferred locking provider.

**Rationale**:
- Modules enforce separation of concerns (vpc, cluster, backup are independently testable)
- Hetzner Object Storage keeps all data in EU (GDPR) and is cost-negligible (~€0.023/GB)
- hcloud Terraform provider (v1.x) is stable and actively maintained
- k3s over managed k8s saves ~€120/month (no Hetzner managed Kubernetes fee)

---

### Project Structure

```text
infrastructure/
├── main.tf                     # Root: wires all modules together
├── variables.tf                # Root-level input variables
├── outputs.tf                  # Root-level outputs (kubeconfig, IPs)
├── versions.tf                 # Provider version locks
├── terraform.tfvars.example    # Example values (committed, no secrets)
├── .terraform-version          # Pinned Terraform version (e.g. 1.8.5)
│
├── modules/
│   ├── vpc/                    # Hetzner private network + firewall
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── cluster/                # k3s nodes (control-plane + workers)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── scripts/
│   │       ├── install-k3s-server.sh   # Control-plane init script
│   │       └── install-k3s-agent.sh    # Worker join script
│   └── backup/                 # Backup CronJob manifests + bucket
│       ├── main.tf             # Object Storage bucket + k8s Secret
│       ├── variables.tf
│       ├── outputs.tf
│       └── manifests/
│           └── backup-cronjob.yaml     # k8s CronJob template
│
└── environments/
    └── staging/                # Staging-specific var overrides
        ├── main.tf             # Imports root modules with staging vars
        └── backend.tf          # Remote state config for staging
```

---

### Layer Structure

```text
┌──────────────────────────────────────────────────────────────┐
│  Terraform Root (main.tf)                                    │
│  Wires modules, passes outputs between them                  │
├───────────────┬──────────────┬───────────────────────────────┤
│  module/vpc   │ module/cluster│  module/backup               │
│  - HCloud     │ - Control     │  - Object Storage bucket     │
│    Network    │   plane       │  - k8s Secret (credentials)  │
│  - Subnet     │ - Worker      │  - CronJob manifest          │
│  - Firewall   │ - k3s install │                              │
└───────────────┴──────────────┴───────────────────────────────┘
                        │
        ┌───────────────▼───────────────────┐
        │  Hetzner Cloud (hcloud API)       │
        │  - Servers (CX21, CX31)           │
        │  - Private Network + Subnet       │
        │  - Firewalls                      │
        │  - SSH Keys                       │
        │  - Object Storage buckets         │
        └───────────────────────────────────┘
```

---

### Provider & Version Configuration (`versions.tf`)

```hcl
terraform {
  required_version = ">= 1.8.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.47"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token   # from HCLOUD_TOKEN env var or tfvars (secret)
}
```

---

### Remote State Backend Design

**Primary**: Terraform Cloud (free tier — 1 workspace, state locking included)

```hcl
# environments/staging/backend.tf
terraform {
  cloud {
    organization = "virtualcloset"
    workspaces {
      name = "virtualcloset-staging"
    }
  }
}
```

**Fallback**: Hetzner Object Storage (S3-compatible, no native locking — process discipline required)

```hcl
# environments/staging/backend.tf (fallback option)
terraform {
  backend "s3" {
    bucket                      = "virtualcloset-tfstate"
    key                         = "staging/terraform.tfstate"
    region                      = "eu-central-1"            # placeholder (required by AWS provider)
    endpoint                    = "https://fsn1.your-objectstorage.com"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    force_path_style            = true
    access_key                  = var.hcloud_s3_access_key  # secret — never in tfvars
    secret_key                  = var.hcloud_s3_secret_key  # secret — never in tfvars
  }
}
```

> **Limitation**: Hetzner Object Storage doesn't support DynamoDB-style state locking. If using the S3 fallback, only one operator should run `terraform apply` at a time. Use Terraform Cloud for true concurrent safety.

---

### Module: VPC (`modules/vpc/`)

**Resources**:

```hcl
# Hetzner private network
resource "hcloud_network" "main" {
  name     = "${var.cluster_name}-network"
  ip_range = "10.0.0.0/16"
}

resource "hcloud_network_subnet" "nodes" {
  network_id   = hcloud_network.main.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

# Firewall: minimal attack surface
resource "hcloud_firewall" "main" {
  name = "${var.cluster_name}-firewall"

  # Allow SSH from admin CIDRs only
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.admin_cidrs
  }
  # Allow k3s API from admin CIDRs (kubectl access)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "6443"
    source_ips = var.admin_cidrs
  }
  # Allow HTTP/HTTPS (ingress to apps)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  # k3s flannel VXLAN (inter-node, private network only)
  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "8472"
    source_ips = ["10.0.0.0/16"]
  }
  # kubelet metrics (inter-node)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "10250"
    source_ips = ["10.0.0.0/16"]
  }
}
```

**Inputs**: `cluster_name`, `admin_cidrs`
**Outputs**: `network_id`, `subnet_id`, `firewall_id`

---

### Module: Cluster (`modules/cluster/`)

**Topology**:

```text
Control Plane (CX21 — 2vCPU/4GB/40GB)
  - k3s server (API + etcd + scheduler)
  - Taint: node-role.kubernetes.io/control-plane:NoSchedule
  - Label: virtualcloset.io/role=control-plane
  - Private IP: 10.0.1.10

Worker Node (CX31 — 2vCPU/8GB/80GB)
  - k3s agent
  - Runs: PostgreSQL, Redis, RabbitMQ, MinIO, FastAPI, Celery, Frontend
  - Label: virtualcloset.io/role=worker
  - Label: virtualcloset.io/workload=stateful (for StatefulSet scheduling)
  - Private IP: 10.0.1.11
```

**Key Resources**:

```hcl
resource "hcloud_server" "control_plane" {
  name        = "${var.cluster_name}-control-plane"
  server_type = "cx21"
  image       = "ubuntu-24.04"
  location    = var.datacenter_location   # "nbg1" (Nuremberg, EU)
  ssh_keys    = [hcloud_ssh_key.admin.id]
  firewall_ids = [var.firewall_id]

  network {
    network_id = var.network_id
    ip         = "10.0.1.10"
  }

  # Install k3s server via remote-exec
  provisioner "remote-exec" {
    inline = [
      "curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=${var.k3s_version} sh -s - server",
      "--disable=traefik",                      # Use own ingress
      "--flannel-iface=eth1",                   # Use private network for flannel
      "--node-ip=10.0.1.10",
      "--advertise-address=10.0.1.10",
      "--node-label=virtualcloset.io/role=control-plane",
      "--tls-san=${self.ipv4_address}",          # Public IP in SAN for kubectl
    ]
    connection {
      type        = "ssh"
      user        = "root"
      private_key = file(var.ssh_private_key_path)
      host        = self.ipv4_address
    }
  }
}

resource "hcloud_server" "worker" {
  name        = "${var.cluster_name}-worker-1"
  server_type = "cx31"
  image       = "ubuntu-24.04"
  location    = var.datacenter_location
  ssh_keys    = [hcloud_ssh_key.admin.id]
  firewall_ids = [var.firewall_id]

  network {
    network_id = var.network_id
    ip         = "10.0.1.11"
  }

  depends_on = [hcloud_server.control_plane]

  provisioner "remote-exec" {
    inline = [
      "curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=${var.k3s_version} K3S_URL=https://10.0.1.10:6443 K3S_TOKEN=${local.k3s_token} sh -s - agent",
      "--node-label=virtualcloset.io/role=worker",
      "--node-label=virtualcloset.io/workload=stateful",
      "--node-ip=10.0.1.11",
      "--flannel-iface=eth1",
    ]
    connection {
      type        = "ssh"
      user        = "root"
      private_key = file(var.ssh_private_key_path)
      host        = self.ipv4_address
    }
  }
}
```

**Kubeconfig retrieval**:

```hcl
# Retrieve kubeconfig from control plane after install
data "remote_file" "kubeconfig" {
  conn {
    host        = hcloud_server.control_plane.ipv4_address
    user        = "root"
    private_key = file(var.ssh_private_key_path)
  }
  path = "/etc/rancher/k3s/k3s.yaml"
  depends_on = [hcloud_server.control_plane]
}

output "kubeconfig" {
  value     = replace(data.remote_file.kubeconfig.content, "127.0.0.1", hcloud_server.control_plane.ipv4_address)
  sensitive = true
}
```

**Inputs**: `cluster_name`, `k3s_version`, `network_id`, `firewall_id`, `datacenter_location`, `ssh_private_key_path`
**Outputs**: `control_plane_public_ip`, `worker_public_ip`, `kubeconfig` (sensitive), `k3s_token` (sensitive)

---

### Module: Backup (`modules/backup/`)

**Backup CronJob Design**:

```yaml
# modules/backup/manifests/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: default
spec:
  schedule: "0 2 * * *"          # 02:00 UTC daily
  concurrencyPolicy: Forbid       # Never run concurrent backups
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: postgres:15-alpine    # pg_dump + aws-cli (or s3cmd)
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-backup-credentials
                  key: password
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: object-storage-credentials
                  key: access_key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: object-storage-credentials
                  key: secret_key
            command:
            - /bin/sh
            - -c
            - |
              set -e
              TIMESTAMP=$(date +%Y%m%d_%H%M%S)
              BACKUP_FILE="backup_${TIMESTAMP}.sql.gz"
              echo "Starting backup: ${BACKUP_FILE}"
              pg_dump -h postgres -U postgres virtual_closet | gzip > /tmp/${BACKUP_FILE}
              aws s3 cp /tmp/${BACKUP_FILE} s3://virtualcloset-backups/${BACKUP_FILE} \
                --endpoint-url https://fsn1.your-objectstorage.com
              echo "Backup complete: ${BACKUP_FILE}"
              rm /tmp/${BACKUP_FILE}
          nodeSelector:
            virtualcloset.io/role: worker
```

**Terraform resources in module**:

```hcl
# Object Storage bucket for backups
resource "hcloud_object_storage_bucket" "backups" {   # or equivalent hcloud resource
  name   = "virtualcloset-backups-${var.environment}"
  # Lifecycle policy: delete objects older than 30 days
}

# k8s Secret with Object Storage credentials (applied via kubernetes provider)
resource "kubernetes_secret" "object_storage_credentials" {
  metadata {
    name      = "object-storage-credentials"
    namespace = "default"
  }
  data = {
    access_key = var.object_storage_access_key
    secret_key = var.object_storage_secret_key
  }
}

# Apply CronJob manifest
resource "kubernetes_manifest" "backup_cronjob" {
  manifest = yamldecode(templatefile("${path.module}/manifests/backup-cronjob.yaml", {
    environment = var.environment
  }))
  depends_on = [kubernetes_secret.object_storage_credentials]
}
```

---

### Root Variables Design (`variables.tf`)

```hcl
variable "hcloud_token" {
  type        = string
  sensitive   = true
  description = "Hetzner Cloud API token. Set via HCLOUD_TOKEN env var."
}

variable "cluster_name" {
  type    = string
  default = "virtualcloset-staging"
}

variable "datacenter_location" {
  type    = string
  default = "nbg1"              # Nuremberg, EU
  validation {
    condition     = contains(["nbg1", "fsn1", "hel1"], var.datacenter_location)
    error_message = "Must be an EU datacenter: nbg1, fsn1, or hel1."
  }
}

variable "k3s_version" {
  type    = string
  default = "v1.29.4+k3s1"     # Pinned — update intentionally
}

variable "admin_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed SSH and kubectl access."
  # Example: ["203.0.113.0/32"]  — developer static IPs
}

variable "ssh_private_key_path" {
  type      = string
  sensitive = true
  default   = "~/.ssh/id_rsa"
}

variable "environment" {
  type    = string
  default = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Must be staging or production."
  }
}

variable "object_storage_access_key" {
  type      = string
  sensitive = true
}

variable "object_storage_secret_key" {
  type      = string
  sensitive = true
}
```

---

### Persistent Volume Strategy

**Provisioner**: k3s built-in `local-path-provisioner` (enabled by default, no installation needed)

```yaml
# StorageClass created automatically by k3s
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
```

**PV allocation per StatefulSet**:

| Service | PVC Size | Node | Path |
|---------|----------|------|------|
| PostgreSQL | 20Gi | worker | /opt/local-path-provisioner/pvc-postgres |
| Redis | 2Gi | worker | /opt/local-path-provisioner/pvc-redis |
| MinIO | 50Gi | worker | /opt/local-path-provisioner/pvc-minio |
| RabbitMQ | 5Gi | worker | /opt/local-path-provisioner/pvc-rabbitmq |

**Non-HA acknowledgment**: All PVs are local to the worker node. If the worker node fails, stateful data is inaccessible until it recovers. Daily backups to Object Storage are the primary data protection mechanism.

---

### Security Design

| Concern | Approach |
|---------|----------|
| Hetzner API token | Never in Terraform state; passed via `HCLOUD_TOKEN` env var or CI secret |
| SSH access | Key-based only; password auth disabled; only from `admin_cidrs` |
| kubeconfig | Generated as sensitive Terraform output; stored in CI/CD secrets vault; not committed to git |
| k3s node token | Sensitive Terraform output; rotated on cluster recreate |
| Object Storage credentials (backup) | Stored as k8s Secret; never in Terraform state or git |
| Firewall | Default-deny inbound; SSH and k3s API limited to admin CIDRs only |
| GDPR | All servers in EU datacenters (nbg1, fsn1, hel1); Object Storage in EU region |
| Sensitive Terraform outputs | All secrets marked `sensitive = true`; never printed in plan/apply output |

---

### NFR Implementation

| NFR | Requirement | Design Approach |
|-----|------------|-----------------|
| Reproducibility | Fresh clone → working cluster | Terraform modules + pinned versions + `terraform.tfvars.example` |
| GDPR compliance | EU data residency | `datacenter_location` constrained to EU; validation rule enforced |
| Cost control | Staging ≤ €30/month | CX21 (~€4/mo) + CX31 (~€11/mo) + Object Storage (~€1/mo) = ~€16/mo |
| Backup reliability | Daily backups, 30-day retention | CronJob at 02:00 UTC; Object Storage lifecycle policy; restore tested |
| Cluster scalability | Add worker nodes without downtime | Terraform `count` on worker resource; add node, `terraform apply` |
| State safety | No state corruption | Terraform Cloud (preferred) or S3 backend with documented locking discipline |
| k3s version control | Predictable upgrades | `k3s_version` variable pinned; upgrade is explicit var change + apply |

---

### Integration Points

| Integration | Configuration | Notes |
|------------|--------------|-------|
| Terraform Cloud | `cloud {}` block in backend.tf | Free tier; state locking included |
| Hetzner Cloud API | `hcloud_token` var / `HCLOUD_TOKEN` env | API token scoped to project |
| Hetzner Object Storage | S3-compatible endpoint `fsn1.your-objectstorage.com` | Used for both tfstate fallback and backups |
| k8s API (post-cluster) | kubeconfig Terraform output → CI/CD secret | Used by bolts 039, 040, 041, 042 |
| GitHub Actions (bolt 040) | Kubeconfig stored as GitHub secret `KUBECONFIG_STAGING` | CI/CD pipelines reference this cluster |
