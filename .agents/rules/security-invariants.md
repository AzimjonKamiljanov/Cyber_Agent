---
trigger: glob
globs: "src/cyber_agent/policy/*.py, src/cyber_agent/tools/*.py, src/cyber_agent/killswitch/*.py, config/*.toml, scripts/manual/*.sh, systemd/*"
description: "Security rules for policy engine, tools, kill switch, config and system scripts."
---
# Security rules for policy/tools/system files
- The LLM proposes `{tool,args}`; only backend code decides ALLOW / CONFIRM / DENY.
- Validate args with strict schemas (reject unknown fields). Every tool: timeout, rate limit, output cap.
- Confirmation token = one action_id + hash of normalized args + expiry (default 60 s) + single use.
- Paths: `resolve()`, must stay under `~/cyber-workspace`; reject `..`, symlink/hard-link escapes; never touch `.env`, `.ssh`, profiles.
- Subprocess: argv list, no `shell=True`, minimal env without secrets, process-group tracking, bubblewrap when executing allowlisted commands.
- Untrusted content marks the session tainted; tainted sessions need stronger YELLOW confirmation.
- Any change here needs a matching test in `tests/security/`.
