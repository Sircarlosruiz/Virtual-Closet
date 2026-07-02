# ADR-034: S3 Backend for Terraform State

## Status
Accepted (replaces Terraform Cloud + Hetzner Object Storage fallback)

## Context
Terraform state needs a remote backend with locking to prevent concurrent modifications. The previous approach used Terraform Cloud as primary with Hetzner Object Storage as fallback.

## Decision
Use **AWS S3** as the Terraform state backend with **DynamoDB** for state locking.

### Configuration
- **Bucket**: `virtualcloset-tfstate`
- **Key**: `staging/terraform.tfstate`
- **Region**: us-west-2
- **Encryption**: Server-side encryption with KMS
- **Locking**: DynamoDB table `virtualcloset-tfstate-lock`

## Consequences

### Positive
- Native AWS integration — no external service dependency
- State locking via DynamoDB (prevents concurrent applies)
- S3 versioning for state history
- KMS encryption for state at rest
- Lower cost than Terraform Cloud ($0.023/GB for S3)

### Negative
- Requires DynamoDB table creation (one-time setup)
- S3 + DynamoDB is AWS-specific

### Setup
```bash
# One-time: Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name virtualcloset-tfstate-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2

# Create S3 bucket
aws s3 mb s3://virtualcloset-tfstate --region us-west-2
aws s3api put-bucket-versioning \
  --bucket virtualcloset-tfstate \
  --versioning-configuration Status=Enabled
```

## Supersedes
Previous decision to use Terraform Cloud with Hetzner Object Storage fallback.
