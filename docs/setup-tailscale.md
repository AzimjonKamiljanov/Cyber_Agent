# Tailscale & Tailscale Serve Configuration Guide

This guide details the procedure to securely connect your Poco F6 Pro smartphone to Cyber Agent running on your Lenovo Legion workstation without opening any public router ports or using Tailscale Funnel.

---

## 1. Security Architecture (MASTER_PLAN §7.6)
- **Zero Public Surface:** Cyber Agent binds strictly to `127.0.0.1:8000`.
- **Private Tailnet Access:** Connection is mediated solely over Tailscale WireGuard mesh encryption.
- **Tailscale Serve (HTTPS):** Generates trusted Let's Encrypt TLS certificates inside the tailnet. This enables Web Audio / microphone permissions in Chrome on Android.
- **Funnel Prohibition:** Tailscale Funnel is **strictly forbidden**. The service must never be accessible from the public internet.

---

## 2. Step-by-Step Configuration

### Step 1: Install & Authenticate Tailscale on Workstation
Review and follow `scripts/manual/02-install-tools.md` to install Tailscale on Ubuntu:
```bash
sudo tailscale up --operator=$USER
```

### Step 2: Install Tailscale on Poco F6 Pro
1. Install **Tailscale** from Google Play Store on your Poco F6 Pro.
2. Sign in with the exact same Tailscale identity (Google or GitHub account) used on your laptop.
3. Verify both devices appear active in your Tailscale admin console or via:
   ```bash
   tailscale status
   ```

### Step 3: Enable MagicDNS & HTTPS Certificates
1. Open the [Tailscale Admin Console](https://login.tailscale.com/admin/dns).
2. Enable **MagicDNS**.
3. Under **HTTPS Certificates**, enable automated provisioning.

### Step 4: Expose Gateway via Tailscale Serve
Execute `scripts/manual/03-tailscale-serve.sh` or run manually:
```bash
# Verify Tailscale Funnel is completely OFF
tailscale funnel status

# Route private HTTPS port 443 to local 127.0.0.1:8000
tailscale serve https / http://127.0.0.1:8000
```

---

## 3. Verification Commands (Strict Check)
Verify that network invariants are preserved:

1. **Check Serve Status:**
   ```bash
   tailscale serve status
   # Must show: https://<laptop-name>.<tailnet>.ts.net proxying to http://127.0.0.1:8000
   ```

2. **Check Funnel Status (Must be OFF):**
   ```bash
   tailscale funnel status
   # Expected output: Funnel is not running. / Funnel is off.
   ```

3. **Check Local Socket Bindings:**
   ```bash
   ss -tulpn | grep 8000
   # Must show binding to 127.0.0.1:8000 ONLY. Never 0.0.0.0:8000.
   ```

---

## 4. Connecting from Poco F6 Pro
1. Turn on Tailscale VPN in your Android Quick Settings.
2. Open Chrome and navigate to:
   `https://<your-laptop-name>.<tailnet>.ts.net`
3. Enter your `CYBER_PAIRING_TOKEN` from `.env` and click **Saqlash**.
4. Grant microphone access when prompted.
