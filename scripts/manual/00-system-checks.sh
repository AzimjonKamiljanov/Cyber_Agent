#!/usr/bin/env bash
# scripts/manual/00-system-checks.sh
# System checks requiring elevated privileges (sudo).
# RUN THIS MANUALLY AS THE MACHINE OWNER.

set -euo pipefail

echo "=== Cyber Agent: Privileged System Checks ==="

# Check Wake-on-LAN support and active mode on ethernet NIC
echo "[1] Checking Wake-on-LAN for enp6s0..."
sudo ethtool enp6s0 | grep -i "wake-on" || echo "ethtool wake-on query completed"

# Check active listening ports (verify nothing public is listening)
echo "[2] Checking listening sockets (should be 127.0.0.1 only for local dev)..."
sudo ss -tulpn | grep -E "(:8000|:11434|tailscale)" || echo "No conflicting ports open"

# Check systemd user lingering status for cyber user (needed for background services)
echo "[3] Checking systemd user lingering..."
loginctl show-user "$(whoami)" | grep "Linger" || echo "Linger check complete"
# To enable lingering if needed: sudo loginctl enable-linger "$(whoami)"

echo "=== System checks complete ==="
