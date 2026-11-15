# Manual Tool Installation Guide

> **Note to Owner:** Review all scripts and official commands before running them in your shell. Never run untrusted installer pipes blindly.

---

## 1. `uv` (Fast Python Package & Project Manager)
`uv` is already present at `/home/cyber/.local/bin/uv` on this workstation.
If you need to update it or ensure it is accessible on system `$PATH`:
```bash
# Official standalone installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```
Ensure `~/.local/bin` is in your `$PATH` in `~/.bashrc` or `~/.zshrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## 2. Ollama (Local LLM Runtime for Mode C)
Required for Stage S3 (offline fallback and privacy mode):
```bash
# Official installation script
curl -fsSL https://ollama.com/install.sh | sh

# Verify service is running
systemctl status ollama

# Pull recommended model for S3
ollama pull qwen2.5:7b-instruct-q4_K_M  # or qwen3:8b when released/configured
```

---

## 3. Tailscale (Private Mesh VPN & Tailscale Serve for Phone PWA)
Required for Stage S1 to securely reach the laptop from your Poco F6 Pro without opening router ports or using Tailscale Funnel:
```bash
# Official installation script
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate and bring up interface
sudo tailscale up

# Verify tailscale status
tailscale status
tailscale ip -4
```
Ensure both your laptop and Poco F6 Pro are on the same Tailscale tailnet.
