# ADR-032: Managed EKS over Self-Managed k3s

## Status
Accepted (replaces previous self-managed k3s on Hetzner decision)

## Context
Virtual Closet needs a Kubernetes cluster for staging and production deployments. The previous decision was to use self-managed k3s on Hetzner VMs for cost optimization. The infrastructure provider has been changed to AWS, and the team prefers managed Kubernetes to reduce operational burden.

## Decision
Use **AWS EKS** (Elastic Kubernetes Service) with managed node groups instead of self-managed k3s.

### Configuration
- **Region**: us-west-2 (Oregon)
- **Kubernetes version**: 1.30
- **Node group**: 2x t3.large (2 vCPU, 8 GB RAM)
- **Scaling**: min=1, max=3, desired=2

## Consequences

### Positive
- AWS manages control plane (API server, etcd, scheduler)
- Automatic Kubernetes version upgrades
- No SSH access to control plane needed
- Integrated with AWS IAM for authentication
- Built-in CloudWatch monitoring
- EBS CSI driver for persistent storage
- No k3s install scripts to maintain

### Negative
- Higher cost than self-managed k3s (~$73/month for EKS control plane alone)
- AWS-specific — less portable
- EKS version lag behind upstream (currently 1.30 vs k8s 1.31)

### Neutral
- Node groups still require patching (EKS AMI updates)
- kubeconfig generated via `aws eks update-kubeconfig` (IAM-based)

## Supersedes
Previous decision to use self-managed k3s on Hetzner (CX21 + CX31).
