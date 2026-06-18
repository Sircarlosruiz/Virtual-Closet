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
  # Set via HCLOUD_TOKEN environment variable — never hardcode
  token = var.hcloud_token
}

provider "kubernetes" {
  config_path = local_file.kubeconfig.filename
}
