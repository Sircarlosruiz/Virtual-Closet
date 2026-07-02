# ADR-035: ingress-nginx with NLB on EKS

## Status
Accepted (replaces previous hostNetwork on k3s worker decision)

## Context
EKS does not have a built-in ingress controller. An ingress controller is required to route external HTTP/HTTPS traffic to the frontend and backend services.

Options evaluated:

1. **AWS Load Balancer Controller (ALB)**: Native AWS integration, provisions ALBs per Ingress. More expensive (~$16/month per ALB), but deep AWS integration.

2. **ingress-nginx + NLB (Network Load Balancer)**: Deploy ingress-nginx as a Deployment with a LoadBalancer Service annotated to create an NLB. NLB forwards traffic to the nginx pods. ~$16/month for NLB.

3. **ingress-nginx + hostNetwork**: Not viable on EKS — nodes are in private subnets with no public IPs.

## Decision
Use **ingress-nginx with NLB** deployed as a Deployment with `service.beta.kubernetes.io/aws-load-balancer-type: nlb` annotation.

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb"
```

Ingress resources in `virtual-closet-staging` use `ingressClassName: nginx`.

## Consequences

**Positive:**
- NLB provides static IPs and DNS name for ingress
- Nodes in private subnets — no direct public exposure
- Standard ingress-nginx features: TLS termination, cert-manager, proxy-body-size
- NLB handles health checking and cross-AZ load balancing

**Negative / Constraints:**
- NLB costs ~$16/month
- DNS must point to NLB hostname (not node IP)
- NLB does not do TLS termination (handled by ingress-nginx)
