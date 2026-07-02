# ADR-038: AWS IAM Credentials for EKS Access from GitHub Actions

## Status
Accepted (replaces previous kubeconfig Secret approach for k3s)

## Context
GitHub Actions needs to authenticate to the Kubernetes cluster to deploy manifests. The previous approach used a base64-encoded kubeconfig stored as a GitHub environment secret (`KUBE_CONFIG_STAGING`) for bare-metal k3s access. With the migration to AWS EKS, IAM-based authentication is available.

## Decision
Use **AWS IAM credentials** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) stored as GitHub environment secrets. The CI workflow uses `aws-actions/configure-aws-credentials@v4` followed by `aws eks update-kubeconfig` to generate a short-lived kubeconfig.

### IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "eks:DescribeCluster",
      "ecr:GetAuthorizationToken",
      "ecr:BatchGetImage",
      "ecr:PutImage"
    ],
    "Resource": "*"
  }]
}
```

## Consequences

### Positive
- No static kubeconfig tokens to rotate
- EKS integrates natively with AWS IAM
- Credentials can be scoped via IAM policies
- `aws eks update-kubeconfig` generates short-lived tokens (15 min)

### Negative
- Requires IAM user management
- AWS credentials in GitHub secrets (rotate quarterly)

### Rotation
```bash
aws iam delete-access-key --user-name virtualcloset-ci --access-key-id <OLD>
aws iam create-access-key --user-name virtualcloset-ci
# Update GitHub secrets
```

## Supersedes
Previous decision to use base64-encoded kubeconfig Secret for bare-metal k3s access.
