#!/usr/bin/env bash
# scripts/manual/08-install-timer.sh
# Installs and activates cyber-morning.timer as a user systemd unit (No sudo required).

set -euo pipefail

TARGET_DIR="$HOME/.config/systemd/user"
mkdir -p "$TARGET_DIR"

echo "==> 1. Copying user units to $TARGET_DIR..."
cp systemd/cyber-morning.service "$TARGET_DIR/"
cp systemd/cyber-morning.timer "$TARGET_DIR/"

echo "==> 2. Reloading user systemd daemon..."
systemctl --user daemon-reload

echo "==> 3. Enabling and starting cyber-morning.timer..."
systemctl --user enable --now cyber-morning.timer

echo "==> 4. Checking timer status..."
systemctl --user status cyber-morning.timer --no-pager || true

echo "Muvaffaqiyatli: Har kuni ertalab 08:00 da ertalabki xulosa avtomatik yangilanadi."
