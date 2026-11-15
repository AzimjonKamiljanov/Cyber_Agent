# Cyber Agent — Project State

Live tracking of active stages, decisions, and system verification status.

---

## Current Status
- **Current Stage:** Stage S4 — Laptop Control (Wayland, Dual Monitor, Isolated Browser, Sandbox)
- **Status:** Completed (Gate G4 Ready for Approval)
- **Active Branch:** `stage/s4-laptop-control`
- **Next Gate:** Gate G4 (Desktop probe, decision 0005, 5 desktop tools, isolated browser, bwrap sandbox, 18 red team tests pass)

---

## Stage Progress Log
| Stage | Name | Status | Gate Passed | Report |
|---|---|---|---|---|
| **S0** | Constitution & Workspace Bootstrap | Completed | Passed G0 | `docs/reports/stage-0-report.uz.md` |
| **S1** | Voice Core | Completed | Passed G1 | `docs/reports/stage-1-report.uz.md` |
| **S2** | Safety Kernel & Tools v1 (MVP) | Completed | Passed G2 (Merged to main) | `docs/reports/stage-2-report.uz.md` |
| **S3** | Local Brain & Uzbek Voice | Completed | Passed G3 (Merged to main) | `docs/reports/stage-3-report.uz.md` |
| **S4** | Laptop Control (Wayland) | Completed | Passed G4 (97 tests pass) | `docs/reports/stage-4-report.uz.md` |
| **S5** | Second Brain & Calendar | Planned | Pending G5 | — |
| **S6** | Hardening & v1.0 Release | Planned | Pending G6 | — |

---

## Hardware & Architecture Snapshot
- **Host / OS:** Legion, Ubuntu 26.04.1 LTS, Kernel 7.0.0-43-generic, GNOME 50.1 Wayland
- **Displays:** Dual-monitor setup: eDP-1 (2560x1600 at 1.33x scale factor, logical 1920x1200) + SWK 27" (1920x1080 at 1.0x)
- **CPU / RAM:** AMD Ryzen 9 9955HX (16C/32T, AVX-512) | 30 GiB RAM
- **GPU:** NVIDIA GeForce RTX 5070 Laptop (8151 MiB VRAM measured, Driver 595.99.02, CUDA 13.2)
- **Gateway Binding:** `127.0.0.1:8000` (FastAPI WebSocket + Tailscale Serve HTTPS)
- **Voice Provider:** `gemini-3.8-live` audio-to-audio streaming via `google-genai==3.3.0`
- **Client Interface:** Vanilla JS PWA (AudioWorklet 16 kHz capture, 24 kHz playback)

---

## Active Decisions Log
- `docs/decisions/0001-live-sdk-notes.md`: Real signatures for `google-genai` Live API.
- `docs/decisions/0003-transport.md`: Transport evaluation criteria (FastAPI WebSocket vs LiveKit).
- `docs/decisions/0004-cuda-stack.md`: Blackwell RTX 5070 CUDA stack and PyAV resampler fix.
- `docs/decisions/0005-desktop-backend.md`: Desktop automation backend adoption (Native AT-SPI + Portals).
- `docs/MASTER_PLAN.md` §3 (D1–D18).

---

## Open Issues / Pending User Tests
- [USER-TEST-REQUIRED] 5-minute terminal test via `uv run python scripts/live_terminal_test.py`.
- [USER-TEST-REQUIRED] Mobile test with Poco F6 Pro + Huawei FreeArc earbuds over Tailscale Serve.
- [USER-TEST-REQUIRED] GNOME desktop input verification: run `scripts/manual/07-desktop-control-setup.sh` and test live input injection.
