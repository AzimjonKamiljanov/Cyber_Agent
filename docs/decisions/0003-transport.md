# Decision Record 0003: Transport Protocol (FastAPI WebSocket vs LiveKit)

**Date:** 2026-11-15  
**Status:** DRAFT (Awaiting Owner G1 Benchmark Results)  
**Reference:** MASTER_PLAN §3 (Decision D4)

---

## 1. Context & Architectural Alternatives
To stream real-time bidirectional audio between the mobile device (Poco F6 Pro + Huawei FreeArc earbuds) and Cyber Agent on the Lenovo Legion workstation over Tailscale, two transport options were considered:

1. **Option A: FastAPI WebSocket + Vanilla PWA (Default)**
   - Custom lightweight protocol: 16 kHz PCM16 binary chunks over WebSocket.
   - Low complexity, zero external servers/daemons, native AudioWorklet resampling.
2. **Option B: Self-Hosted LiveKit Server + WebRTC Client (Contingency)**
   - Industrial WebRTC SFU, handles adaptive bitrate, built-in jitter buffers, packet loss concealment.
   - Adds operational overhead: running LiveKit daemon, TURN server, and heavier client SDK.

---

## 2. Objective Acceptance Criteria (Gate G1)
Per MASTER_PLAN §3 D4, the system defaults to Option A (FastAPI WebSocket) **unless** empirical testing on the physical hardware fails any of the following gates:

| Metric | Target Gate | Description |
|---|---|---|
| **P50 Latency** | $\le 2.0\text{ s}$ | End-of-speech to first audible reply |
| **P95 Latency** | $\le 3.0\text{ s}$ | 95th percentile worst-case latency |
| **Audio Dropouts** | 0 drops | Clean audio stream over continuous 5-minute conversation |
| **FreeArc Echo** | No feedback loop | Open-ear acoustic leakage mitigated by browser echoCancellation + PTT |
| **Barge-in** | $\le 200\text{ ms}$ | Immediate playback flush upon user speech / PTT activation |

---

## 3. Empirical Test Results (To be filled by Owner)
*Tested on Poco F6 Pro + Huawei FreeArc over Tailscale Serve HTTPS:*

- **Measured P50 Latency:** [ ]
- **Measured P95 Latency:** [ ]
- **Audio Glitches / Dropouts:** [ ]
- **Echo Leakage Observed:** [ ]
- **Barge-in Responsiveness:** [ ]

---

## 4. Final Verdict & Adoption
<!-- TO BE COMPLETED BY OWNER AFTER TESTING -->
- **Adopted Transport:** 
- **Rationale:** 
