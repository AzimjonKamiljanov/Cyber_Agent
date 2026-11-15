# Cyber Agent

Cyber Agent is a personal, voice-first, JARVIS-style AI assistant for its owner (Azimjon). It converses in Uzbek through a smartphone (Poco F6 Pro) and earbuds (Huawei FreeArc), controls a personal workstation (Lenovo Legion Pro 5, Ubuntu 26.04 Wayland) through a policy-controlled tool layer, and runs at zero extra cost using free tiers and local AI models.

---

## Architecture Overview

1. **Voice Gateway**:
   - **Mode A (Live)**: Low-latency audio-to-audio streaming via `gemini-3.8-live` over WebSocket.
   - **Mode B (Cascade)**: Local `faster-whisper` STT -> Gemini Flash text -> Local TTS.
   - **Mode C (Local/Private)**: Local `faster-whisper` STT -> Local Ollama (`qwen3:8b`) -> Local TTS.
2. **Policy Engine**:
   - Enforces 3 tiers: GREEN (auto-allow), YELLOW (preview card + token confirmation), and RED (denied).
   - Sandboxes executions inside bubblewrap (`bwrap`) with no ambient shell.
3. **Transport & Network**:
   - PWA client connects over Tailscale Serve HTTPS/WSS inside private tailnet.
   - Services bind exclusively to `127.0.0.1`.
4. **Kill Switch**:
   - Out-of-band `cyber-killswitch` daemon activated via hotkey (`Super+Shift+Escape`) or PWA STOP button.

---

## 12-Week Roadmap & Stages

| Stage | Name | Key Deliverables | Gate |
|---|---|---|---|
| **S0** | Constitution & Workspace Bootstrap | Antigravity pack, workspace skeleton, hardware audit | G0 |
| **S1** | Voice Core | Gemini 3.8 Live WebSocket gateway, PWA PTT, barge-in, STOP | G1 |
| **S2** | Safety Kernel & MVP Tools | Policy engine, 10+ safe tools, kill switch service, 30-sentence benchmark | G2 (MVP) |
| **S3** | Local Brain & Uzbek Voice | faster-whisper, local TTS, Ollama fallback, 100-sentence benchmark | G3 |
| **S4** | Workstation Control | Wayland AT-SPI inspection, isolated Playwright, bubblewrap execution | G4 |
| **S5** | Second Brain | SQLite memory, morning brief, Google Calendar integration | G5 |
| **S6** | Hardening & v1.0 Release | Red-team test suite, backup/restore, ADB phone control, packaging | G6 (v1.0) |

---

## Prerequisites & Installation

- **OS**: Ubuntu 26.04 LTS (x86_64)
- **Runtime**: Python 3.12+ managed via `uv`
- **GPU**: NVIDIA RTX 5070 Laptop (CUDA >= 12.8)
- **Local Services**: Ollama, Tailscale

### Quickstart (Stage S0)
```bash
# Verify customization pack
python3 scripts/check_customizations.py

# Lint codebase
ruff check .
```
