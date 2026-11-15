# Ubuntu Setup & Secrets Configuration

This guide details how to configure your environment, credentials, and network security for Cyber Agent.

---

## 1. Secrets & Environment Configuration

> [!CAUTION]
> The builder agent must **NEVER** see, read, log, or commit your API keys. You must create and manage the `.env` file manually.

### Step 1: Create Google AI Studio API Key
1. Open [Google AI Studio](https://aistudio.google.com/) in your browser.
2. Sign in with your Google account (eligible for Google AI Pro credits or free tier quotas).
3. Click **Get API key** -> **Create API key**.
4. Copy your newly created API key.

### Step 2: Generate Pairing Token
A pairing token is used to authenticate WebSocket connections between your Poco F6 Pro PWA and the FastAPI gateway:
```bash
# Generate a cryptographically secure 32-character hex token
openssl rand -hex 16
```

### Step 3: Populate `.env`
Copy `.env.example` to `.env` in the repository root:
```bash
cp .env.example .env
chmod 600 .env
```
Edit `.env` using your preferred text editor (e.g. `nano .env` or `ghostty`) and insert your credentials:
```env
GEMINI_API_KEY=your_actual_api_key_here
CYBER_LIVE_MODEL=gemini-3.8-live
CYBER_HOST=127.0.0.1
CYBER_PORT=8000
CYBER_PRIVACY_MODE=false
CYBER_DATA_DIR=./data
CYBER_ADDRESS_AS=Azimjon
CYBER_WORKSPACE_DIR=/home/cyber/cyber-workspace
CYBER_PAIRING_TOKEN=your_generated_pairing_token_here
```
Verify permissions:
```bash
ls -la .env
# Must show: -rw------- 1 cyber cyber ... .env
```

---

## 2. Directory Initialization
Create the agent's isolated workspace directory:
```bash
mkdir -p ~/cyber-workspace
```

---

## 3. Python Environment Sync
Ensure `uv` is installed and sync the environment:
```bash
export PATH="$HOME/.local/bin:$PATH"
uv sync
```

---

## 4. Tailscale Serve Setup (For Stage S1)
When Stage S1 is active, expose the local FastAPI port (8000) over Tailscale Serve (HTTPS inside your tailnet):
```bash
# Verify Tailscale Funnel is OFF (prohibited)
tailscale funnel status

# Expose local port 8000 over Tailscale Serve HTTPS
tailscale serve https / http://127.0.0.1:8000
```
This allows your Poco F6 Pro to open `https://<your-laptop-tailnet-name>.ts.net` in Chrome with full microphone access enabled by HTTPS.
