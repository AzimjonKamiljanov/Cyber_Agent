# Hardware & System Audit — Stage S0

Audit date: 2026-11-15  
Audited by: Cyber Agent (Antigravity builder)  
Status: **VERIFIED (Measured via non-destructive commands)**

---

## 1. Operating System & Desktop Environment
- **Distribution:** Ubuntu 26.04.1 LTS (Codename: resolute)
- **Kernel:** Linux Legion 7.0.0-43-generic (x86_64 GNU/Linux)
- **Session Type:** `wayland` (`$XDG_SESSION_TYPE=wayland`)
- **Desktop Environment:** GNOME Shell 50.1

---

## 2. Processor (CPU)
- **Model:** AMD Ryzen 9 9955HX 16-Core Processor
- **Topology:** 16 Cores, 32 Threads (2 threads per core, 1 socket)
- **Frequency:** Max 5460.5 MHz, Min 1217.1 MHz
- **Caches:** L1d: 768 KiB, L1i: 512 KiB, L2: 16 MiB, L3: 64 MiB
- **Vector Extensions:** AVX, AVX2, AVX-VNNI, AVX-512 (f, dq, ifma, cd, bw, vl, bf16, vbmi, vbmi2, vnni, bitalg, vpopcntdq, vp2intersect)
- **Assessment:** Exceptionally fast multi-threaded performance. Highly suitable for running `faster-whisper` on CPU via AVX-512, preserving GPU VRAM for LLM & TTS.

---

## 3. Memory & Storage
- **Physical RAM:** 30 GiB total (8.8 GiB used, 15 GiB free, 21 GiB available)
- **Swap:** 8.0 GiB total (0 B used)
- **Disk Storage (`nvme0n1`):** 953.9 GB NVMe SSD
  - Root partition (`nvme0n1p5`): 400 GB ext4 mounted on `/`
  - Windows partitions: `nvme0n1p3` (552.8 GB ntfs), `nvme0n1p4` (892 MB ntfs)
  - EFI: `nvme0n1p1` (200 MB vfat)

---

## 4. Graphics & CUDA (GPU)
- **GPU Device:** NVIDIA GeForce RTX 5070 Laptop GPU
- **VRAM Total:** **8151 MiB (~8 GB VRAM)** [Measured by nvidia-smi]
- **Driver Version:** 595.99.02
- **CUDA Version:** 13.2
- **Power & Thermal:** 12W / 105W cap, Temp 47°C
- **Status:** Operational. Meets all requirements for S1–S3. Due to 8 GB VRAM capacity, concurrent model execution strategy (CPU for STT, GPU for Ollama 8B Q4 & TTS) is recommended.

---

## 5. Tool & Binary Availability
| Tool | Status | Path / Version |
|---|---|---|
| `uv` | Installed | `/home/cyber/.local/bin/uv` (uv 0.13.8) |
| `python3.12` | Installed | `/home/cyber/.local/bin/python3.12` (CPython 3.12.8) |
| `system python` | Installed | `/usr/bin/python3` (Python 3.14.4) |
| `bwrap` (bubblewrap) | Installed | `/usr/bin/bwrap` |
| `ffmpeg` | Installed | `/home/cyber/.local/bin/ffmpeg` (v7.0.2-static) |
| `ollama` | **Missing** | To be installed via `scripts/manual/02-install-tools.md` |
| `tailscale` | **Missing** | To be installed via `scripts/manual/02-install-tools.md` |

---

## 6. Networking
- **Ethernet (`enp6s0`):** UP, IP `10.20.0.233/20`, 100Mb/s Full Duplex
- **Wi-Fi (`wlo1`):** UP, IP `10.50.6.181/20`
- **Wake-on-LAN check:** Requires privileged access (`sudo ethtool enp6s0`). Added to `scripts/manual/00-system-checks.sh` for user verification.
