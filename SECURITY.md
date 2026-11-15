# Security Model — Cyber Agent

Cyber Agent has the "lethal trifecta": access to private data + reads untrusted external content (web, email, files) + ability to execute actions on the operating system.

Security is enforced in **backend code and operating system boundaries, never in prompt wording alone**.

---

## 1. Action Permission Tiers (§7.1)

| Tier | Policy Verdict | Behavior | Examples |
|---|---|---|---|
| **GREEN** | ALLOW | Audited execution within scope, rate limits, timeouts | Read time, system status (psutil/nvidia-smi), volume, search within workspace, open allowlisted app, draft message (no send) |
| **YELLOW** | CONFIRM | Requires on-screen preview card + single-use one-time token | Write/move workspace file, git commit, browser form fill, GUI click/type, run allowlisted command in bubblewrap |
| **RED** | DENY | Tool does not exist in registry; impossible to invoke | `sudo`, arbitrary shell (`shell=True`), `rm -rf`, secrets/keys, password managers, banking, force push, changing policy/audit |

---

## 2. Policy Engine Invariants (§7.2)
1. **Model Proposes, Engine Decides**: The model proposes `{tool, args}`. The policy engine evaluates arguments and returns `ALLOW | CONFIRM | DENY`.
2. **Strict Validation**: All tool parameters are validated using Pydantic schemas. Extra or unknown fields are rejected.
3. **UI-Only Confirmation**: Only physical user interaction with the UI (PWA confirm button) can validate an action. Spoken "yes" is never sufficient.
4. **Token Binding**: Confirmation tokens are bound to `action_id`, a cryptographic hash of normalized arguments, and a 60-second expiry. Tokens cannot be reused or transferred.
5. **Idempotency**: All mutating operations require a unique `request_id` and `idempotency_key`.

---

## 3. Defense Against Prompt Injection & Session Taint (§7.4)
- Web pages, emails, PDFs, user-generated documents, and tool outputs are treated as **untrusted data**.
- Untrusted data is never promoted to instruction status.
- Once untrusted data enters the context window, the session is marked as **tainted**. Tainted sessions require elevated confirmation cards with explicit taint warnings for any subsequent YELLOW actions.

---

## 4. Filesystem Sandboxing (§7.5)
- All agent file operations are jailed inside `~/cyber-workspace`.
- Paths are canonicalized with `resolve()`. Traversal attempts (`..`), symlink escapes, and access outside the jail are rejected.
- Access to `.env`, `.ssh`, browser profiles, system files, and keyrings is blocked unconditionally.
- Destructive file deletion tools do not exist.

---

## 5. Network Security (§7.6)
- Services bind strictly to `127.0.0.1`.
- Remote access from mobile devices is routed through **Tailscale Serve** inside the user's private tailnet.
- **Tailscale Funnel and router port forwarding are strictly prohibited.**
- WebSocket connections require a random `CYBER_PAIRING_TOKEN` and strict Origin validation.

---

## 6. Secrets & Audit Logging (§7.7)
- Secrets and API keys are stored in `.env` (chmod 600) or OS keyring.
- Secrets are stripped from prompts, logs, and error messages via the redaction engine.
- Audit logs are written in append-only JSONL format with SHA-256 hash chaining.

---

## 7. Hardware & Software Kill Switch (§7.8)
- `cyber-killswitch` runs as an independent systemd user service listening on a dedicated Unix domain socket.
- Triggers:
  - System hotkey: `Super + Shift + Escape`
  - Mobile UI: PWA STOP button
- Triggering the kill switch immediately halts all action dispatch, invalidates pending confirmation tokens, terminates active subprocess process groups, drops the audio session, and logs the emergency halt.
