#!/bin/bash
# Install k3s control-plane node
# Environment variables expected: K3S_VERSION, NODE_IP, PUBLIC_IP
set -euo pipefail

echo "Installing k3s server (control-plane) version ${K3S_VERSION}"
echo "Private IP: ${NODE_IP} | Public IP: ${PUBLIC_IP}"

# Wait for apt lock to be available
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
  echo "Waiting for apt lock..."
  sleep 5
done

# Install prerequisites
apt-get update -qq
apt-get install -y -qq curl

# Install k3s server
# --disable=traefik  : use our own ingress controller (defined in k8s manifests)
# --flannel-iface    : use private network interface for pod-to-pod traffic
# --node-ip          : advertise private IP for inter-node communication
# --advertise-address: private IP for k3s API on the cluster network
# --tls-san          : include public IP in TLS SAN so kubectl works over public IP
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="${K3S_VERSION}" \
  sh -s - server \
    --disable=traefik \
    --flannel-iface=eth1 \
    --node-ip="${NODE_IP}" \
    --advertise-address="${NODE_IP}" \
    --tls-san="${PUBLIC_IP}" \
    --node-label="virtualcloset.io/role=control-plane" \
    --node-taint="node-role.kubernetes.io/control-plane:NoSchedule"

# Wait for k3s API to become ready
echo "Waiting for k3s API server..."
until kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml get nodes >/dev/null 2>&1; do
  sleep 3
done

echo "k3s control-plane ready"
