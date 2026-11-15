# Cyber Agent — Project State

Live tracking of active stages, decisions, and system verification status.

---

## Current Status
- **Current Stage:** Stage S1 — Voice Core
- **Status:** Completed (Awaiting Owner Gate Approval G1)
- **Active Branch:** `stage/s1-voice-core`
- **Next Gate:** Gate G1 (5-minute Uzbek conversation from phone+FreeArc; echo/PTT verdict; LiveKit decision recorded)

---

## Stage Progress Log
| Stage | Name | Status | Gate Passed | Report |
|---|---|---|---|---|
| **S0** | Constitution & Workspace Bootstrap | Completed | Passed G0 | `docs/reports/stage-0-report.uz.md` |
| **S1** | Voice Core | Completed | Pending G1 Approval | `docs/reports/stage-1-report.uz.md` |
| **S2** | Safety Kernel & Tools v1 (MVP) | Planned | Pending G2 | — |
| **S3** | Local Brain & Uzbek Voice | Planned | Pending G3 | — |
| **S4** | Laptop Control (Wayland) | Planned | Pending G4 | — |
| **S5** | Second Brain & Calendar | Planned | Pending G5 | — |
| **S6** | Hardening & v1.0 Release | Planned | Pending G6 | — |

---

## Hardware & Architecture Snapshot
- **Host / OS:** Legion, Ubuntu 26.04.1 LTS, Kernel 7.0.0-43-generic, GNOME 50.1 Wayland
- **CPU / RAM:** AMD Ryzen 9 9955HX (16C/32T, AVX-512) | 30 GiB RAM
- **GPU:** NVIDIA GeForce RTX 5070 Laptop (8151 MiB VRAM measured, Driver 595.99.02, CUDA 13.2)
- **Gateway Binding:** `127.0.0.1:8000` (FastAPI WebSocket + Tailscale Serve HTTPS)
- **Voice Provider:** `gemini-3.8-live` audio-to-audio streaming via `google-genai==3.3.0`
- **Client Interface:** Vanilla JS PWA (AudioWorklet 16 kHz capture, 24 kHz playback)

---

## Active Decisions Log
- `docs/decisions/0001-live-sdk-notes.md`: Real signatures for `google-genai` Live API.
- `docs/decisions/0003-transport.md`: Transport evaluation criteria (FastAPI WebSocket vs LiveKit).
- `docs/MASTER_PLAN.md` §3 (D1–D18).

---

## Open Issues / Pending User Tests
- [USER-TEST-REQUIRED] 5-minute terminal test via `uv run python scripts/live_terminal_test.py`.
- [USER-TEST-REQUIRED] Mobile test with Poco F6 Pro + Huawei FreeArc earbuds over Tailscale Serve.
- [USER-TEST-REQUIRED] Transport evaluation verdict entry in `docs/decisions/0003-transport.md`.
