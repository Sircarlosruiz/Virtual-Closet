#!/bin/bash
# Install k3s worker (agent) node and join the cluster
# Environment variables expected: K3S_VERSION, K3S_URL, K3S_TOKEN, NODE_IP
set -euo pipefail

echo "Installing k3s agent (worker) version ${K3S_VERSION}"
echo "Joining cluster at ${K3S_URL} | Private IP: ${NODE_IP}"

# Wait for apt lock
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
  echo "Waiting for apt lock..."
  sleep 5
done

apt-get update -qq
apt-get install -y -qq curl

# Install k3s agent and join cluster
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION="${K3S_VERSION}" \
  K3S_URL="${K3S_URL}" \
  K3S_TOKEN="${K3S_TOKEN}" \
  sh -s - agent \
    --flannel-iface=eth1 \
    --node-ip="${NODE_IP}" \
    --node-label="virtualcloset.io/role=worker" \
    --node-label="virtualcloset.io/workload=stateful"

echo "k3s agent joined cluster successfully"
