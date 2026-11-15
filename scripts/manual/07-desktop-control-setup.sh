#!/usr/bin/env bash
# scripts/manual/07-desktop-control-setup.sh
# Cyber Agent — Stage S4 Desktop Control Setup & Candidate Tooling
# Run by the owner: sets up desktop control permissions and candidate tools.
set -euo pipefail

echo "=== Cyber Agent: Stage S4 Desktop Control Setup ==="

# 1. Check uinput group for non-root keyboard/mouse emulation
echo "1. Checking /dev/uinput permissions..."
if [ -w /dev/uinput ]; then
    echo "   ✓ /dev/uinput is writable by current user."
else
    echo "   ! /dev/uinput requires udev rule for non-root access."
    echo "   To enable non-root input emulation without sudo prompt each time:"
    echo "   sudo usermod -aG input \$USER"
    echo "   echo 'KERNEL==\"uinput\", GROUP=\"input\", MODE=\"0660\"' | sudo tee /etc/udev/rules.d/99-uinput.rules"
    echo "   sudo udevadm trigger"
fi

# 2. Check Rust/Cargo for building computer-use-linux
echo "2. Checking Rust toolchain..."
if command -v cargo >/dev/null 2>&1; then
    echo "   ✓ Cargo is installed: $(cargo --version)"
    echo "   To build computer-use-linux:"
    echo "   cargo install --git https://github.com/agent-sh/computer-use-linux"
else
    echo "   ! Cargo/Rust not detected."
    echo "   If you want to install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
fi

# 3. GNOME 50 Wayland session note
echo "3. GNOME 50 Wayland session notes:"
echo "   - Cyber Agent default backend: Native AT-SPI accessibility bus + XDG Desktop Portals."
echo "   - No screenshot-to-cloud: screen understanding uses semantic AT-SPI tree."
echo "   - Re-login to GNOME may be required after adding your user to the input group."

echo "=== Setup check completed ==="
