#!/usr/bin/env bash
# MANUAL STEP — run by the human owner (Azimjon).
# Sets up and enables Cyber Agent systemd user services.

set -euo pipefail

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Cyber Agent: systemd user units installation ==="

mkdir -p "$SYSTEMD_USER_DIR"

# Copy unit files
cp "$REPO_DIR/systemd/cyber-killswitch.service" "$SYSTEMD_USER_DIR/"
cp "$REPO_DIR/systemd/cyber-core.service" "$SYSTEMD_USER_DIR/"

echo "-> Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "-> Enabling and starting cyber-killswitch.service..."
systemctl --user enable cyber-killswitch.service
systemctl --user restart cyber-killswitch.service

echo "-> Enabling and starting cyber-core.service..."
systemctl --user enable cyber-core.service
systemctl --user restart cyber-core.service

echo "-> Checking service status..."
systemctl --user status cyber-killswitch.service --no-pager
systemctl --user status cyber-core.service --no-pager

echo "=== Services installed successfully. ==="
