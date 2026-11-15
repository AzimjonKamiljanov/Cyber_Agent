---
name: hardware-audit
description: Performs a read-only hardware and OS audit of the owner's laptop and writes docs/hardware-audit.md. Use in stage S0 or whenever hardware assumptions must be re-checked.
---
# Hardware audit (read-only)
Run: `lsb_release -a`, `uname -a`, `echo $XDG_SESSION_TYPE`, `gnome-shell --version`, `lscpu`, `free -h`, `nvidia-smi`, `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS`, `python3 --version`, `which uv ollama tailscale bwrap ffmpeg`.
Commands needing sudo are NOT run; list them for the owner instead.
Write results to `docs/hardware-audit.md`: measured VRAM, CUDA driver, session type, tools present/missing.
If `nvidia-smi` fails, state that GPU stages are blocked and stop.
