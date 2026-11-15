# Cyber Agent — Shaxsiy Ovozli AI Assistent (v1.0.0)

Cyber Agent — bu egasi (**Azimjon**) uchun maxsus yaratilgan, o'zbek tilida tabiiy ovoz bilan muloqot qiluvchi shaxsiy AI assistent tizimi.
U smartfon (Poco F6 Pro) va quloqchinlar (Huawei FreeArc) orqali boshqariladi, noutbuk ishchi stolini (Lenovo Legion Pro 5, Ubuntu 26.04 GNOME 50.1 Wayland) xavfsiz boshqaradi va 100% bepul kvotalar hamda mahalliy modellar yordamida tejamkor ishlaydi.

---

## 🚀 Asosiy Imkoniyatlar (v1.0.0)

1. **Uch Bosqichli Tri-Mode Ovozli Arxitektura:**
   - **Mode A (Gemini 3.8 Live):** WebSocket orqali audio-to-audio past kechikishli (P50: ~1.4s) o'zbekcha jonli suhbat, uzilish (barge-in) va live transkripsiya.
   - **Mode B (Cascade):** Mahalliy `faster-whisper` STT -> Gemini Flash LLM -> Mahalliy TTS.
   - **Mode C (Local Brain):** 100% oflayn va maxfiy rejim: mahalliy `faster-whisper` (GPU float16) -> mahalliy Ollama (`qwen2.5:7b-instruct-q4_K_M` / `qwen3:8b`) -> mahalliy TTS.
2. **Qat'iy Xavfsizlik Yadrosi (Safety Kernel):**
   - 3 darajali ruxsat tizimi (**GREEN**, **YELLOW**, **RED**).
   - Tashqi veb yoki taqvim tavsiflaridan keluvchi inyeksiyalarga qarshi **Sessiya Zararlanishi (Taint Tracking)** nazorati.
   - Parol va maxfiy maydonlarga matn kiritishni mutlaqo rad etish (Invariant 1).
   - Parol menejerlari (1Password, Bitwarden, KeePassXC) va bank ilovalarini avtomatik niqoblash.
   - Mustaqil Unix socket va `Super+Shift+Escape` orqali ishlovchi **Favqulodda To'xtatish (Kill Switch)** tizimi.
3. **Noutbuk va Ishchi Stol Boshqaruvi:**
   - Wayland va GNOME 50 muhitida AT-SPI ochiq kirish shinasini o'qish va semantik UI daraxti introspeksiyasi.
   - Ikki monitorli koordinata moslashuvi (eDP-1 2560x1600 masshtab 1.33x + SWK 27" 1920x1080).
   - Alohidalanlangan Playwright brauzeri (`data/browser_profile/`, egasining shaxsiy profiliga aslo tegmaydi).
   - Tarmoqsiz (`--unshare-net`) va minimal tozalangan muhit bilan ishlovchi **Bubblewrap Qumdon (Sandbox)**.
4. **Ikkinchi Miya (Second Brain):**
   - SQLite va FTS5 to'liq matnli qidiruv orqali foydalanuvchi roziligi bilan ma'lumot eslab qolish.
   - `Asia/Tashkent` vaqti bilan doimiy ishlovchi eslatmalar va `notify-send` bildirishnomalari.
   - Har kuni 08:00 da yangilanuvchi **Ertalabki Xulosa (Morning Brief)** va systemd user timer.
   - Read-only Google Calendar integratsiyasi.
   - IT terminlarini (API, Git, Docker, Pytest, Token, Linux) asrovchi **Jonli Tarjimon Rejimi (Translate Mode)**.

---

## 📋 Tizim va Uskunalar Profili

- **Noutbuk:** Lenovo Legion Pro 5
- **OS / Muhit:** Ubuntu 26.04.1 LTS, Kernel 7.0.0-43-generic, GNOME 50.1 Wayland
- **Protsessor:** AMD Ryzen 9 9955HX (16C/32T, AVX-512) | 30 GiB RAM
- **Videokarta:** NVIDIA GeForce RTX 5070 Laptop (8151 MiB VRAM, Driver 595.99.02, CUDA 13.2)
- **Tarmoq va Xavfsizlik:** `127.0.0.1:8000` (FastAPI WebSocket + Tailscale Serve HTTPS)

---

## 🛠️ Tezkor O'rnatish va Ishga Tushirish

### 1. Avtomatik O'rnatish
```bash
bash scripts/install.sh
```

### 2. Tizim Diagnostikasi (Doctor Audit)
```bash
uv run python scripts/doctor.py
```

### 3. Zaxira va Falokatdan Tiklash Sinovi (Disaster Recovery Drill)
```bash
uv run python scripts/restore_drill.py
```

### 4. Barcha Testlarni Ishga Tushirish (119 ta test)
```bash
uv run pytest tests/
```

### 5. Xizmatni Ishga Tushirish
```bash
systemctl --user start cyber-core.service
```

---

## 🔒 Xavfsizlik va Hujjatlar

- **Xavfsizlik Modeli:** [SECURITY.md](SECURITY.md)
- **Tahdidlar Modeli (Threat Model):** [docs/threat-model.md](docs/threat-model.md)
- **Operatsion Qo'llanma va Qoidalar:** [docs/runbook.md](docs/runbook.md)
- **Tizim Arxitekturasi:** [docs/architecture.md](docs/architecture.md)
- **Ubuntu 26.04 Sozlash:** [docs/setup-ubuntu.md](docs/setup-ubuntu.md)
- **Sinov Natijalari va Benchmark:** [docs/benchmark.md](docs/benchmark.md)
