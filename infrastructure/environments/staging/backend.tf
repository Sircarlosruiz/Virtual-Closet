# Terraform Cloud state backend — see ADR-034
# Primary: Terraform Cloud (native locking, free for small teams)
# Fallback: Hetzner Object Storage S3 backend (no locking — documented in ADR-034)
#
# To use Terraform Cloud: authenticate with `terraform login` before `terraform init`
terraform {
  cloud {
    organization = "virtualcloset"
    workspaces {
      name = "virtualcloset-staging"
    }
  }
}

# ─── FALLBACK: Hetzner Object Storage S3 backend ──────────────────────────────
# Uncomment and comment out the cloud{} block above to use S3 fallback.
# WARNING: No state locking — only one operator may run terraform apply at a time.
# See ADR-034 for migration procedure.
#
# terraform {
#   backend "s3" {
#     bucket                      = "virtualcloset-tfstate"
#     key                         = "staging/terraform.tfstate"
#     region                      = "eu-central-1"
#     endpoint                    = "https://fsn1.your-objectstorage.com"
#     skip_credentials_validation = true
#     skip_metadata_api_check     = true
#     skip_region_validation      = true
#     force_path_style            = true
#     # Set via env vars: AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
#   }
# }
