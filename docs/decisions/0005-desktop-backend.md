# Decision Record 0005: Desktop Automation Backend Selection for GNOME 50 / Wayland

## Context
Cyber Agent requires voice-controlled desktop interaction on Ubuntu 26.04.1 LTS running GNOME 50.1 under Wayland with dual monitors (2560x1600 scale 1.33 + 1920x1080 scale 1.0).
Interaction must adhere to strict security invariants:
- Zero screenshots sent to cloud.
- Semantic screen understanding via UI accessibility tree (AT-SPI) and window lists.
- Strict Policy Engine oversight (YELLOW tier confirmations for clicking, typing, and command running).
- Never type into password fields or sensitive windows.

## Evaluated Candidate: `agent-sh/computer-use-linux` (Rust MCP)
- **License:** MIT License (Permissive).
- **Architecture:** Rust-based MCP server interacting with Wayland portals, AT-SPI, and `ydotool`.
- **Readiness Check on Host:**
  - `cargo` / `rustc` is not installed on the workstation.
  - Direct compilation requires human intervention and developer tooling.
  - Window targeting and mouse/keyboard injection on GNOME Wayland require `/dev/uinput` group access (`sudo usermod -aG input $USER`) and a GNOME session logout/login.
- **Security Audit:**
  - Includes `run_shell` tool. Per MASTER_PLAN §8 and §18, Cyber Agent strictly forbids arbitrary shell execution tools. If adopted, `run_shell` must remain permanently disabled.

## Chosen Strategy: Native AT-SPI + XDG Portals + uinput Fallback
**Verdict: FALLBACK ADOPTED (Native Python AT-SPI + Portals)**

### Rationale:
1. **Immediate Zero-Sudo Execution:** The AT-SPI accessibility bus (`org.a11y.Bus`) is already active at `/run/user/1000/at-spi/bus`. Native Python DBus calls inspect active application trees and window states directly without compiling external binaries.
2. **Deterministic Security Boundary:** Built directly into the `cyber_agent.tools.desktop` package under the Stage S2 Policy Engine. All input injection checks target windows against `config/sensitive_windows.toml` and refuses password fields before sending events.
3. **Multi-Monitor Coordinate Normalization:** Automatically accounts for GNOME Mutter fractional scaling (2560x1600 at 1.33x scale factor) and secondary monitor offsets (1920x1080 at 1.0x).
4. **Compatibility Path:** If the owner installs `computer-use-linux` via `scripts/manual/07-desktop-control-setup.sh`, Cyber Agent's tool registry can seamlessly bind its tools as a secondary adapter while keeping `run_shell` OFF.
