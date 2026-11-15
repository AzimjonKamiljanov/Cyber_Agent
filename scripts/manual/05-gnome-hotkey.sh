#!/usr/bin/env bash
# MANUAL STEP — run by the human owner (Azimjon).
# Binds Super+Shift+Escape to scripts/cyber-stop via GNOME settings.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STOP_SCRIPT="$REPO_DIR/scripts/cyber-stop"

echo "=== Cyber Agent: Configuring GNOME Hotkey (Super+Shift+Escape) ==="

if ! command -v gsettings >/dev/null 2>&1; then
    echo "gsettings topilmadi. Faqat GNOME muhitida ishlaydi."
    exit 1
fi

KEY_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/cyber-stop/"

# Fetch current list of custom keybindings
CURRENT=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)

if [[ "$CURRENT" == "@as []" || "$CURRENT" == "[]" ]]; then
    NEW_LIST="['$KEY_PATH']"
elif [[ "$CURRENT" != *"$KEY_PATH"* ]]; then
    NEW_LIST="${CURRENT%]*}, '$KEY_PATH']"
else
    NEW_LIST="$CURRENT"
fi

gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_LIST"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH name "Cyber Agent Emergency STOP"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH command "$STOP_SCRIPT"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH binding "<Super><Shift>Escape"

echo "=== Hotkey o'rnatildi: [Super + Shift + Escape] -> $STOP_SCRIPT ==="
