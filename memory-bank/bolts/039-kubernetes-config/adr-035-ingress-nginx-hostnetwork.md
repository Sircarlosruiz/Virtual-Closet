---
bolt: 039-kubernetes-config
created: 2026-06-18T12:00:00Z
status: accepted
superseded_by: null
---

# ADR-035: ingress-nginx with hostNetwork on Worker Node (Over NodePort + Hetzner LB)

## Context

The k3s cluster installed in bolt 037 has Traefik disabled (`--disable=traefik` flag). An Ingress controller is required to route external HTTP/HTTPS traffic to the frontend and backend services.

Options evaluated:

1. **Re-enable Traefik**: k3s ships with Traefik v2. Re-enabling means updating the k3s install script, which would require reprovisioning the cluster or running `kubectl apply` manually. Couples the ingress controller lifecycle to the k3s version.

2. **ingress-nginx + Hetzner Load Balancer**: Create a LoadBalancer service; Hetzner automatically provisions a cloud LB (~€5.83/month). The LB forwards traffic to the NodePort on the worker. Adds monthly cost and a dependency on Hetzner's LB provisioner (CCM — Cloud Controller Manager) which requires additional installation.

3. **ingress-nginx + hostNetwork DaemonSet on worker**: Deploy the ingress-nginx controller with `hostNetwork: true` targeted to the worker node. The controller binds directly to ports 80/443 on the worker's public IP. No extra cloud resource required. The firewall rules from bolt 037 already open ports 80 and 443 from `0.0.0.0/0`.

4. **MetalLB**: Provides bare-metal LoadBalancer support. Requires additional configuration (IP address pool). Overkill for a single-node staging cluster.

## Decision

Use **ingress-nginx with hostNetwork: true** deployed as a DaemonSet targeting the worker node (`nodeSelector: virtualcloset.io/role: worker`).

The controller runs in the `ingress-nginx` namespace (not `virtual-closet-staging`) and is a cluster-wide component. It is installed once via the official bare-metal manifest, then patched to enable `hostNetwork`.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/baremetal/deploy.yaml

kubectl patch daemonset ingress-nginx-controller \
  -n ingress-nginx \
  --type=json \
  -p='[
    {"op":"add","path":"/spec/template/spec/hostNetwork","value":true},
    {"op":"add","path":"/spec/template/spec/nodeSelector","value":{"virtualcloset.io/role":"worker"}}
  ]'
```

Ingress resources in `virtual-closet-staging` use `ingressClassName: nginx`.

## Consequences

**Positive:**
- No additional cloud cost (vs option 2: ~€5.83/month = ~€70/year)
- No Cloud Controller Manager dependency
- Ports 80/443 already open in Hetzner firewall (bolt 037 VPC module)
- Standard ingress-nginx feature set: TLS termination, cert-manager integration, proxy-body-size annotation for file uploads

**Negative / Constraints:**
- Port 80/443 on the worker IP are now reserved by the nginx controller. No other DaemonSet or hostPort pod can bind those ports on the same node.
- If the worker node is reprovisioned, nginx-controller pod must be rescheduled manually (or wait for DaemonSet reconciliation, ~30s).
- hostNetwork exposes the controller pod to the host network stack — minor security tradeoff vs an isolated Service+LB.
- Scaling to 2 worker nodes: the DaemonSet will run on both, but both will bind 80/443 on their respective IPs. DNS round-robin or Hetzner LB would be needed to distribute traffic. At that scale, switching to option 2 (Hetzner LB) is recommended.

**Read when**: Adding worker nodes to the cluster, troubleshooting Ingress 404s, configuring TLS certificates, planning horizontal scaling beyond 1 worker.
