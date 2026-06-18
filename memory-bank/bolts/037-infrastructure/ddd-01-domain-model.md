---
stage: domain-model
bolt: 037-infrastructure
created: 2026-06-17T17:00:00Z
---

## Static Model: infrastructure-provisioning

### Entities

- **HetznerCluster**: Properties: name, datacenter (eu-central, nbg1/fsn1/hel1), k3s_version, node_count, kubeconfig_path — Business Rules: exactly 1 control-plane node; ≥1 worker node; control-plane must be healthy before workers join; k3s version pinned and documented
- **Node**: Properties: id, role (control-plane | worker), server_type (CX21 | CX31), image (ubuntu-24.04), location, labels[], taints[], private_ip, public_ip — Business Rules: CX21 reserved for control-plane only; CX31 for workloads; each node must have role label `node.kubernetes.io/role`; control-plane tainted `NoSchedule` for app workloads
- **HetznerNetwork**: Properties: id, name, ip_range (10.0.0.0/16), subnet_ip_range (10.0.1.0/24), zone — Business Rules: all nodes must be attached to the same private network; internal communication uses private IPs only; public IPs only for SSH and ingress
- **Firewall**: Properties: id, name, rules[] — Business Rules: inbound rules: SSH (22) from admin CIDRs only, HTTP (80) + HTTPS (443) from anywhere, k3s API (6443) from admin CIDRs; all other inbound blocked by default; outbound unrestricted
- **PersistentVolume**: Properties: name, storage_class (local-path), capacity, access_mode (ReadWriteOnce), node_affinity — Business Rules: local-path-provisioner creates PVs automatically on the worker node's host filesystem; not replicated across nodes (acceptable: StatefulSets with ReadWriteOnce); backup compensates for non-HA storage
- **BackupJob**: Properties: id, schedule (cron), source (PostgreSQL database), destination (Hetzner Object Storage bucket), retention_days (30), encryption — Business Rules: daily execution at 02:00 UTC; must verify upload success before cleanup; retention enforced by lifecycle policy on Object Storage; backup must be testable via restore procedure
- **ObjectStorageBucket**: Properties: name, region, access_key, secret_key, endpoint — Business Rules: separate bucket per environment (staging, production); lifecycle policy enforces 30-day retention; credentials stored as k8s Secrets, not in Terraform state
- **TerraformState**: Properties: backend_type (s3-compatible | hcloud-object-storage), bucket, key, lock_table — Business Rules: state must be stored remotely (never local); state locking prevents concurrent modifications; state encryption at rest required; Terraform version pinned in `.terraform-version`
- **TerraformModule**: Properties: name, version, inputs[], outputs[] — Business Rules: modules are composable units (vpc, cluster, backup); each module has clearly defined inputs and outputs; no hardcoded values — all from variables

---

### Value Objects

- **ServerType**: type_name (CX21 | CX31), vcpu, ram_gb, disk_gb, monthly_cost_eur — Constraints: server type selection is immutable after provisioning without destroy+recreate; chosen based on workload profile
- **NodeLabel**: key, value — Constraints: keys follow `kubernetes.io/` or custom `virtualcloset.io/` prefix conventions; labels drive pod scheduling via `nodeSelector`
- **NodeTaint**: key, value, effect (NoSchedule | NoExecute | PreferNoSchedule) — Constraints: control-plane taint `node-role.kubernetes.io/control-plane:NoSchedule` prevents app workloads from landing on control-plane
- **CIDRBlock**: cidr — Constraints: must be valid CIDR notation; private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- **BackupRetentionPolicy**: retention_days (30), min_backups (7) — Constraints: at least 7 backups must exist regardless of age; enforced on Object Storage via lifecycle rules
- **CronSchedule**: expression (cron format), timezone (UTC) — Constraints: backup at 02:00 UTC to avoid production peak hours

---

### Aggregates

- **HetznerCluster** (Aggregate Root): Members: Node[], HetznerNetwork, Firewall[] — Invariants: ≥1 node with role=control-plane must be healthy; all nodes share the same private network; cluster kubeconfig valid and accessible; k3s version uniform across all nodes
- **InfrastructureProject** (Aggregate Root for Terraform): Members: TerraformModule[], TerraformState, variable_definitions[] — Invariants: all modules must reference same provider version; state backend configured before any `terraform apply`; all sensitive outputs marked `sensitive = true`
- **BackupSystem** (Aggregate Root): Members: BackupJob, ObjectStorageBucket, BackupRetentionPolicy — Invariants: BackupJob must have verified Object Storage credentials before first run; retention policy applied to bucket lifecycle; restore procedure tested and documented before going to production

---

### Domain Events

- **NodeProvisioned**: Trigger: Terraform creates Hetzner server — Payload: node_id, node_role, server_type, private_ip, public_ip
- **ClusterInitialized**: Trigger: k3s installs on control-plane node — Payload: k3s_version, cluster_name, kubeconfig_available
- **WorkerJoined**: Trigger: k3s agent joins cluster — Payload: worker_node_id, control_plane_ip, join_token_used
- **BackupCompleted**: Trigger: pg_dump upload to Object Storage succeeds — Payload: backup_file, size_bytes, duration_seconds, timestamp
- **BackupFailed**: Trigger: pg_dump or upload error — Payload: error_message, timestamp, next_retry
- **RestoreValidated**: Trigger: restore procedure successfully recovers database — Payload: backup_file_used, rows_verified, duration_seconds
- **TerraformApplied**: Trigger: `terraform apply` completes — Payload: resources_created, resources_changed, resources_destroyed

---

### Domain Services

- **ClusterProvisioner**: Orchestrates node provisioning sequence (VPC → nodes → k3s install → worker join); enforces ordering; waits for control-plane health before workers join; Dependencies: HetznerNetwork, Node provisioning, k3s install scripts
- **BackupScheduler**: Manages pg_dump execution, Object Storage upload, and retention enforcement; runs as Kubernetes CronJob; Dependencies: BackupJob, ObjectStorageBucket, PostgreSQL connection
- **RestoreValidator**: Executes restore-from-backup procedure against a temporary database; verifies row counts; Dependencies: ObjectStorageBucket, BackupJob, temporary PostgreSQL instance
- **FirewallManager**: Applies Hetzner firewall rules to nodes; ensures admin CIDRs are whitelisted for API access; Dependencies: Firewall, Node[]
- **TerraformStateManager**: Initializes remote backend, enforces locking, handles state migration; Dependencies: TerraformState, Object Storage credentials

---

### Repository Interfaces

- **NodeRepository**: Entity: Node — Methods: provision(type, role): Node, deprovision(id): void, get_status(id): NodeStatus, list_by_role(role): Node[]
- **NetworkRepository**: Entity: HetznerNetwork — Methods: create(ip_range): HetznerNetwork, attach_node(network_id, node_id): void, get_private_ip(node_id): str
- **BackupRepository**: Entity: BackupJob — Methods: create_snapshot(): BackupFile, upload(file, bucket): ObjectKey, list_snapshots(bucket): BackupFile[], delete_expired(): void
- **TerraformStateRepository**: Entity: TerraformState — Methods: initialize_backend(): void, lock(): LockID, unlock(lock_id): void, get_current(): StateVersion

---

### Ubiquitous Language

- **control-plane**: The k3s master node (CX21) — manages cluster state, runs kube-apiserver, etcd, scheduler, and controller-manager; tainted to prevent app workload scheduling
- **worker node**: A k3s agent node (CX31) — runs application workloads and stateful services; no cluster management responsibilities
- **kubeconfig**: The YAML file granting authenticated access to the k3s API server; generated by k3s install and secured via Terraform output or SSH retrieval
- **hcloud**: The Hetzner Cloud provider for Terraform; abstracts Hetzner API calls into Terraform resources
- **local-path-provisioner**: A lightweight k3s add-on that creates PersistentVolumes from the node's local filesystem; simple, non-HA, compensated by backup
- **pg_dump**: PostgreSQL's native backup tool; produces a SQL dump of the entire database; used for daily backups to Object Storage
- **Object Storage**: Hetzner's S3-compatible blob storage; used for backup files; lifecycle rules enforce 30-day retention
- **Terraform module**: A reusable, parameterized collection of Terraform resources; each module encapsulates one infrastructure concern (vpc, cluster, backup)
- **remote state backend**: Terraform state stored in Object Storage (S3-compatible) rather than locally; enables team collaboration and prevents state loss
- **state locking**: A mechanism preventing concurrent `terraform apply` operations; implemented via DynamoDB-equivalent lock on the state backend
- **CX21**: Hetzner server type — 2 vCPU, 4 GB RAM, 40 GB SSD; cost-effective for k3s control-plane (low resource requirements)
- **CX31**: Hetzner server type — 2 vCPU, 8 GB RAM, 80 GB SSD; chosen for worker nodes running PostgreSQL StatefulSet, application pods, and Celery workers
- **datacenter region**: Hetzner EU datacenters (nbg1 Nuremberg, fsn1 Falkenstein, hel1 Helsinki); EU region chosen for GDPR compliance
- **node taint**: A Kubernetes mechanism marking a node as unsuitable for certain pods; control-plane uses `NoSchedule` to repel app workloads
- **node label**: A key-value tag on a Kubernetes node; used for pod `nodeSelector` to pin workloads to specific nodes (e.g., GPU, high-memory)
- **30-day retention**: The backup retention window; enforced by Object Storage lifecycle policy; older backups are automatically deleted
