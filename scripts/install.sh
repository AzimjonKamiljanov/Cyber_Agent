#!/usr/bin/env bash
# scripts/install.sh — Production Installer for Cyber Agent v1.0
# Idempotent, safe, and transparent.
# Strictly NO `sudo` inside. Any privileged steps are printed for the user to execute manually.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "================================================================="
echo "        CYBER AGENT v1.0 — INSTALLATION & SETUP"
echo "================================================================="

# 1. Check Python and uv
echo "==> 1. Checking prerequisites..."
if ! command -v uv &>/dev/null; then
    echo "XATO: 'uv' paket menejeri topilmadi."
    echo "Iltimos, avval uv ni o'rnating: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✅ uv topildi: $(uv --version)"

# 2. Workspace directories
echo "==> 2. Preparing workspace and data directories..."
mkdir -p "$PROJECT_ROOT/data/backups"
mkdir -p "$PROJECT_ROOT/data/browser_profile"
mkdir -p "$HOME/cyber-workspace"
mkdir -p "$HOME/.config/cyber-agent"
chmod 700 "$PROJECT_ROOT/data"
chmod 700 "$HOME/cyber-workspace"
echo "✅ Kataloglar tayyorlandi."

# 3. Virtual environment and dependencies
echo "==> 3. Synchronizing Python dependencies via uv..."
uv sync
echo "✅ Python virtual muhiti tayyor."

# 4. Playwright Chromium browser
echo "==> 4. Ensuring Playwright Chromium is installed..."
uv run playwright install chromium
echo "✅ Playwright Chromium brauzeri tayyor."

# 5. Environment configuration
echo "==> 5. Setting up environment (.env)..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    PAIRING_TOKEN=$(openssl rand -hex 16)
    sed -i "s/CYBER_PAIRING_TOKEN=.*/CYBER_PAIRING_TOKEN=$PAIRING_TOKEN/" "$PROJECT_ROOT/.env"
    chmod 600 "$PROJECT_ROOT/.env"
    echo "✅ .env fayli yaratildi va maxfiy ruxsatlar (600) o'rnatildi."
else
    chmod 600 "$PROJECT_ROOT/.env"
    echo "✅ Mavjud .env fayli tekshirildi (600 ruxsatlar)."
fi

# 6. Systemd user services
echo "==> 6. Installing systemd user units..."
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

cp "$PROJECT_ROOT/systemd/cyber-core.service" "$USER_SYSTEMD_DIR/"
cp "$PROJECT_ROOT/systemd/cyber-killswitch.service" "$USER_SYSTEMD_DIR/"
cp "$PROJECT_ROOT/systemd/cyber-morning.service" "$USER_SYSTEMD_DIR/"
cp "$PROJECT_ROOT/systemd/cyber-morning.timer" "$USER_SYSTEMD_DIR/"

systemctl --user daemon-reload
echo "✅ User systemd unitlari o'rnatildi."

# 7. Run system diagnostic doctor
echo "==> 7. Running system doctor diagnostic audit..."
uv run python "$PROJECT_ROOT/scripts/doctor.py" || true

echo "================================================================="
echo "                O'RNATISH YAKUNLANDI!"
echo "================================================================="
echo "Quyidagi ixtiyoriy tizim qadamlarini qo'lda ishga tushirishingiz mumkin:"
echo "1. GNOME klaviatura yorlig'i (Super+Shift+Escape) -> $PROJECT_ROOT/scripts/cyber-stop"
echo "2. uinput ruxsati (Wayland actuations) -> bash $PROJECT_ROOT/scripts/manual/07-desktop-control-setup.sh"
echo "3. Ertalabki xulosa taymerini yoqish -> bash $PROJECT_ROOT/scripts/manual/08-install-timer.sh"
echo "4. Google Calendar OAuth -> docs/setup-google.md"
echo "5. Tizimni ishga tushirish: systemctl --user start cyber-core.service"
echo "================================================================="
