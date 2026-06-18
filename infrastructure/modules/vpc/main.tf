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

resource "hcloud_firewall" "main" {
  name = "${var.cluster_name}-firewall"

  # SSH — admin access only
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.admin_cidrs
  }

  # k3s API server — kubectl access for admin CIDRs only
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "6443"
    source_ips = var.admin_cidrs
  }

  # HTTP — public ingress
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # HTTPS — public ingress
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # flannel VXLAN — inter-node communication on private network only
  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "8472"
    source_ips = ["10.0.0.0/16"]
  }

  # kubelet metrics — inter-node on private network only
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "10250"
    source_ips = ["10.0.0.0/16"]
  }
}
