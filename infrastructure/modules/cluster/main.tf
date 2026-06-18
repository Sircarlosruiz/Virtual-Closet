locals {
  control_plane_private_ip = "10.0.1.10"
  worker_private_ip        = "10.0.1.11"
}

# ─── Control Plane (CX21 — 2vCPU/4GB/40GB) ────────────────────────────────
resource "hcloud_server" "control_plane" {
  name         = "${var.cluster_name}-control-plane"
  server_type  = "cx21"
  image        = "ubuntu-24.04"
  location     = var.datacenter_location
  ssh_keys     = [var.ssh_key_id]
  firewall_ids = [var.firewall_id]

  network {
    network_id = var.network_id
    ip         = local.control_plane_private_ip
  }

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = self.ipv4_address
  }

  provisioner "remote-exec" {
    script = "${path.module}/scripts/install-k3s-server.sh"
    environment = {
      K3S_VERSION = var.k3s_version
      NODE_IP     = local.control_plane_private_ip
      PUBLIC_IP   = self.ipv4_address
    }
  }

  # Wait for network attachment before provisioning
  depends_on = [var.network_id]
}

# ─── Worker Node (CX31 — 2vCPU/8GB/80GB) ──────────────────────────────────
# Runs all application workloads: PostgreSQL, Redis, MinIO, RabbitMQ, backend, frontend
resource "hcloud_server" "worker" {
  name         = "${var.cluster_name}-worker-1"
  server_type  = "cx31"
  image        = "ubuntu-24.04"
  location     = var.datacenter_location
  ssh_keys     = [var.ssh_key_id]
  firewall_ids = [var.firewall_id]

  network {
    network_id = var.network_id
    ip         = local.worker_private_ip
  }

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = self.ipv4_address
  }

  provisioner "remote-exec" {
    script = "${path.module}/scripts/install-k3s-agent.sh"
    environment = {
      K3S_VERSION        = var.k3s_version
      K3S_URL            = "https://${local.control_plane_private_ip}:6443"
      K3S_TOKEN          = data.remote_file.k3s_token.content
      NODE_IP            = local.worker_private_ip
    }
  }

  # Worker joins after control plane is ready and token is available
  depends_on = [hcloud_server.control_plane, data.remote_file.k3s_token]
}

# ─── Retrieve cluster secrets from control plane via SSH ──────────────────
# kubeconfig — contains cluster CA, server endpoint, and admin credentials
data "remote_file" "kubeconfig" {
  conn {
    host        = hcloud_server.control_plane.ipv4_address
    user        = "root"
    private_key = file(var.ssh_private_key_path)
  }
  path       = "/etc/rancher/k3s/k3s.yaml"
  depends_on = [hcloud_server.control_plane]
}

# k3s node join token — needed by worker and future scale-out nodes
data "remote_file" "k3s_token" {
  conn {
    host        = hcloud_server.control_plane.ipv4_address
    user        = "root"
    private_key = file(var.ssh_private_key_path)
  }
  path       = "/var/lib/rancher/k3s/server/node-token"
  depends_on = [hcloud_server.control_plane]
}
