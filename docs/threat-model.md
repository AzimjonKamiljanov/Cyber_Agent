# Cyber Agent — Comprehensive Threat Model

**Version:** 1.0.0  
**Scope:** Cyber Agent System (Stages S0–S6)  
**Standard:** STRIDE & LINDDUN Methodology  
**Target Platform:** Ubuntu 26.04 LTS on Lenovo Legion Pro 5 (AMD Ryzen 9, NVIDIA RTX 5070)

---

## 1. System Assets & Sensitivity Classification

| Asset | Sensitivity | Storage Location | Protection Mechanism |
|---|---|---|---|
| **API Keys & Credentials** | Critical | `.env` (chmod 600), Keyring | Redaction filter, stripped from child process environments |
| **Pairing Token** | Critical | `.env` / Environment | Verified on WebSocket connect, never logged |
| **Audit Trails** | High | `data/audit.jsonl` | SHA-256 cryptographic hash-chain, append-only |
| **User Memory & Reminders** | High | `data/memory.sqlite3` | Local SQLite with FTS5, secret filters, consent flow |
| **Calendar Tokens** | High | `data/calendar_token.json` (chmod 600) | Read-only scope, excluded from git & backups |
| **Workspace Files** | Medium | `~/cyber-workspace` | Jail boundary (`resolve()`), bubblewrap sandbox |
| **Desktop State & Windows** | Medium | GNOME / Wayland | Read-only AT-SPI tree, sensitive window denylist |

---

## 2. Trust Boundaries

```
[ UNTRUSTED EXTERNAL WORLD ]
 (Web pages, Calendar invites, Email, Unverified audio)
           │
           ▼ (Prompt Injection Risk)
   [ TAINT BOUNDARY ] ─── Marks session TAINTED
           │
           ▼
[ NETWORK BOUNDARY ] ─── 127.0.0.1 strictly; Tailscale Serve HTTPS (No Funnel)
           │
           ▼
[ POLICY ENGINE GATE ] ─── GREEN (auto) / YELLOW (UI confirm) / RED (Forbidden)
           │
           ▼
[ EXECUTION SANDBOX ] ─── Bubblewrap (--unshare-net, stripped env, jail root)
```

---

## 3. STRIDE Threat Analysis & Mitigations

### 3.1 Spoofing (Identity & Origin)
- **Threat:** Malicious device on local network tries to connect to FastAPI WebSocket.
- **Mitigation:**
  - Services bind exclusively to `127.0.0.1`.
  - Remote mobile connections require encrypted Tailscale mesh.
  - WebSocket handshakes enforce `CYBER_PAIRING_TOKEN` authentication query parameter.

### 3.2 Tampering (Data & Code Integrity)
- **Threat:** Untrusted web content attempts to tamper with agent policies, command allowlists, or tool registry.
- **Mitigation:**
  - Policy engine and tool definitions are hardcoded and immutable at runtime (`FORBIDDEN_TOOLS`).
  - Confirmation tokens are bound to `action_id`, arguments hash, and 60-second single-use lifetime.
  - Bubblewrap mounts `/usr`, `/bin`, `/lib` as read-only (`--ro-bind`).

### 3.3 Repudiation (Accountability)
- **Threat:** Denying that an action was executed or tampering with past logs.
- **Mitigation:**
  - Audit logger maintains an unbroken SHA-256 hash-chain across every event.
  - Hash chain verifies chronological continuity; any deletion or mutation invalidates the chain.

### 3.4 Information Disclosure (Privacy Leaks)
- **Threat:** Exfiltration of `.env`, SSH keys, or browser passwords via prompt injection or file reading.
- **Mitigation:**
  - Filesystem jail (`resolve_jail_path`) unconditionally rejects `.env`, `.ssh`, and out-of-workspace paths.
  - Isolated Playwright profile stored under `data/browser_profile/` (never touches `~/.config`).
  - Desktop automation driver strictly detects and refuses password/PIN elements (`is_password_field`).
  - Sensitive window denylist (`config/sensitive_windows.toml`) masks password managers and banking apps.
  - Memory filter (`filters.py`) refuses storage of API keys, passwords, PINs, and credit card numbers.

### 3.5 Denial of Service (Resource Exhaustion)
- **Threat:** Fork bomb, infinite loops, or runaway speech processes hogging CPU/GPU.
- **Mitigation:**
  - Subprocess execution enforces strict timeouts (default 30 s) and output size caps (8000 chars).
  - Standalone `cyber-killswitch` daemon on dedicated Unix socket (`/run/user/1000/cyber/cyber-stop.sock`).
  - Hardware hotkey (`Super+Shift+Escape`) and mobile STOP button instantly send `SIGKILL` to tracked process groups and drop the session in under 1 second.

### 3.6 Elevation of Privilege (Unauthorized Execution)
- **Threat:** Attacker uses agent to execute `sudo`, spawn root shells, or run destructive tools (`rm -rf`).
- **Mitigation:**
  - `sudo_command`, `arbitrary_shell`, and `delete_file` are classified as **RED tier** and do not exist in the tool registry.
  - Commands inside sandbox are restricted to an explicit prefix allowlist (`config/command_allowlist.toml`).
  - Bubblewrap runs unprivileged (rootless user namespace).
  - Network access inside sandbox is disabled via `--unshare-net`.

---

## 4. Residual Risks & Operational Assumptions

1. **Host OS Physical Security:** Security model assumes the laptop has full-disk encryption (LUKS) and is physically protected when unattended.
2. **Tailnet Administrator Access:** Assumes the user's Tailscale account is secured with multi-factor authentication (MFA).
3. **Third-Party Model Vulnerabilities:** Cloud LLM (Gemini Live) and local model (Ollama Qwen) may be susceptible to novel adversarial jailbreaks. The system's **deterministic policy kernel and OS sandbox** ensure that even if the model is tricked, it cannot execute unauthorized actions.
