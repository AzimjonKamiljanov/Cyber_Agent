#!/usr/bin/env bash
# scripts/manual/01-install-system-packages.sh
# Installs baseline system libraries required for audio, sandboxing, and Wayland bindings.
# DO NOT RUN AS AN AI AGENT. THE OWNER MUST REVIEW AND RUN THIS MANUALLY.

set -euo pipefail

echo "=== Installing System Packages for Cyber Agent (Stages S1-S2) ==="
echo "Packages to be installed: portaudio19-dev ffmpeg libxkbcommon0 bubblewrap"

sudo apt update
sudo apt install -y \
  portaudio19-dev \
  ffmpeg \
  libxkbcommon0 \
  bubblewrap

echo "=== System packages installation complete ==="
