# Cyber Agent — Operational Runbook & Disaster Recovery

**Version:** 1.0.0  
**Target Platform:** Ubuntu 26.04 LTS (x86_64)

---

## 1. Emergency Kill Switch Operations

### 1.1 Triggering Emergency Halt
- **System Hotkey (Instant):** Press `Super + Shift + Escape` on your laptop.
- **Mobile PWA UI:** Tap the red `STOP` button.
- **CLI Command:** Run `/home/cyber/Cyber_Agent/scripts/cyber-stop`.

### 1.2 Effects of Emergency Halt
1. All pending tool executions and queued background tasks are instantly cancelled.
2. All active subprocess process groups (sandbox, audio processes) are terminated with `SIGKILL`.
3. All pending confirmation tokens are immediately invalidated in SQLite.
4. Active audio streaming sessions are terminated.
5. An emergency halt record is written to the audit log.

### 1.3 Recovering After Emergency Halt
To re-enable operations after investigating the cause:
```bash
# Restart the core daemon
systemctl --user restart cyber-core.service
```

---

## 2. Disaster Recovery Scenarios

### 2.1 Scenario A: Lost or Stolen Mobile Device
If the phone paired with Cyber Agent is lost or stolen:
1. **Rotate Pairing Token Immediately:**
   Edit `.env` on your laptop:
   ```bash
   # Generate a new cryptographic pairing token
   NEW_TOKEN=$(openssl rand -hex 16)
   sed -i "s/CYBER_PAIRING_TOKEN=.*/CYBER_PAIRING_TOKEN=$NEW_TOKEN/" .env
   ```
2. **Restart the Core Gateway:**
   ```bash
   systemctl --user restart cyber-core.service
   ```
   All existing active WebSocket connections are terminated immediately, and connections with the old token are rejected.
3. **Revoke Tailscale Node Access:**
   Open Tailscale Admin Console and remove the lost device from your tailnet.

### 2.2 Scenario B: Revoked or Compromised Gemini API Key
If your Google Cloud / AI Studio API key is compromised or revoked:
1. **Update `.env`:**
   ```bash
   sed -i "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=YOUR_NEW_KEY/" .env
   chmod 600 .env
   ```
2. **Immediate Offline Fallback (Mode C):**
   Even without an API key, Cyber Agent remains 100% operational in **Mode C (Local Brain)**:
   - Voice STT: Local `faster-whisper` on GPU.
   - Brain: Local `qwen2.5:7b-instruct` / `qwen3:8b` via Ollama.
   - Voice TTS: Local offline audio engine.

### 2.3 Scenario C: Cloud Quota Exhaustion
If the Gemini Live API returns `RESOURCE_EXHAUSTED` (HTTP 429):
1. **Zero-Cost Circuit Breaker:**
   - Cyber Agent **never** triggers auto-paid fallbacks or incurs cloud bills.
   - The Model Router automatically switches the active mode to **Mode C (Local Brain)**.
2. **Notification:**
   - The agent informs the user in Uzbek: *"Bulut kvotasi tugadi. Barcha amallar xavfsiz oflayn rejimda davom etmoqda."*

---

## 3. Backup and Full Restoration

### 3.1 Creating a Manual Backup
```bash
uv run python -m scripts.backup
```
Creates a timestamped compressed archive in `data/backups/cyber_backup_YYYYMMDD_HHMMSS.tar.gz`.

### 3.2 Restoring from Backup
```bash
uv run python -m scripts.backup --restore data/backups/cyber_backup_YYYYMMDD_HHMMSS.tar.gz
```

### 3.3 Running Automated Disaster Recovery Drill
```bash
uv run python scripts/restore_drill.py
```
Verifies full end-to-end backup, disaster wipe, and restore cycle in an isolated sandbox.
