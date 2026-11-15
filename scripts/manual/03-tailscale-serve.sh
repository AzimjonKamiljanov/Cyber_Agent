#!/usr/bin/env bash
# scripts/manual/03-tailscale-serve.sh
# Configures Tailscale Serve to securely proxy HTTPS inside the private tailnet.
# DO NOT RUN AS AN AI AGENT. THE OWNER MUST REVIEW AND EXECUTE THIS MANUALLY.

set -euo pipefail

echo "=== Cyber Agent: Tailscale Serve Setup ==="

# 1. Enforce Funnel is disabled
echo "[1] Checking Tailscale Funnel status (must be OFF)..."
if tailscale funnel status 2>/dev/null | grep -iE "(active|enabled|listening)"; then
    echo "ERROR: Tailscale Funnel is detected as ACTIVE! Turning it OFF immediately..."
    tailscale funnel reset || true
fi
echo "Tailscale Funnel verified OFF."

# 2. Check local application binding
echo "[2] Verifying Cyber Agent is bound to 127.0.0.1:8000..."
if ! ss -tulpn | grep "127.0.0.1:8000" > /dev/null 2>&1; then
    echo "Notice: Cyber Agent is not running on 127.0.0.1:8000 yet. Start it with: uv run python -m cyber_agent.main"
fi

# 3. Configure Tailscale Serve
echo "[3] Starting Tailscale Serve proxy for port 8000..."
tailscale serve https / http://127.0.0.1:8000

# 4. Display current status and URL
echo ""
echo "=== Tailscale Serve Active Configuration ==="
tailscale serve status
echo ""
echo "Open the HTTPS URL shown above on your Poco F6 Pro Chrome browser."
