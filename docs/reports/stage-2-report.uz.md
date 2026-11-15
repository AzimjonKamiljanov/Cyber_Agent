# Bosqich hisoboti — S2: Safety Kernel, Tools v1 & MVP

**Sana:** 2026-11-15  
**Filial:** `stage/s2-safety-tools`  
**Holat:** Yakunlandi (G2 MVP Gate tasdig'i kutilmoqda)  

---

## 1. Xulosa
Stage S2 muvaffaqiyatli yakunlandi va Cyber Agent MVP (Minimum Viable Product) darajasiga yetkazildi. Tizimda mustahkam xavfsizlik yadrosi (SHA-256 zanjirli JSONL audit, 3 pog'onali GREEN/YELLOW/RED policy dvigateli, sessiya zaharlanishini kuzatish va SQLite-da 60 soniyalik bir martalik tasdiq tokenlari) qurildi. 10 ta xavfsiz va qumloqlangan dastlabki asboblar (bwrap izolatsiyasi, workspace jail) ishga tushirildi, Gemini Live NON_BLOCKING orkestratori va PWA mobil tasdiqlash kartochkalari ulandi. Alohida mustaqil jarayon sifatida ishlovchi Favqulodda to'xtatish (Kill Switch) tizimi yaratildi (jarayon guruhlarini 0.94 ms ichida to'xtatadi), barcha 10 ta Red-Team hujumi to'liq qaytarildi va 100 ta gapdan iborat o'zbekcha benchmarkda 96% aniqlik qayd etildi.

---

## 2. Nima qilindi
1. **Audit va Redaksiya (`src/cyber_agent/audit/`):**
   - `redaction.py`: API kalitlari (`AIzaSy...`), bearer tokenlar, maxfiy lug'atlar va audio baytlarni tozalash.
   - `logger.py`: SHA-256 hash zanjirli append-only JSONL logeri va fayl rotatsiyasi (10 MB).
2. **Xavfsizlik Dvigateli va Tasdiqlar (`src/cyber_agent/policy/`):**
   - `permissions.py`: `PolicyTier` (GREEN, YELLOW, RED), `PolicyVerdict` (ALLOW, CONFIRM, DENY).
   - `taint.py`: Tashqi veb/xat manbalaridan kelgan sessiyalarni zaharlangan (`is_tainted`) deb belgilovchi tracker.
   - `confirmations.py`: SQLite-ga asoslangan, 60s muddatli, argumentlar heshiga bog'langan bir martalik tokenlar ombori.
   - `engine.py`: Taqiqlangan buyruqlarni (RED) so'zsiz to'suvchi va YELLOW amallar uchun mobil tasdiq talab qiluvchi baholash mexanizmi.
3. **Asboblar Registri va Qattiq Sxemalar (`src/cyber_agent/tools/`):**
   - `schemas.py`: Pydantic `extra='forbid'` bilan inyeksiyani inkor etuvchi qat'iy modellar.
   - `registry.py`: Taqiqlangan asboblarni ro'yxatdan o'tkazishni taqiqlovchi, timeout va idempotency tekshiruviga ega boshqaruvchi.
   - `workspace_jail.py`: `~/cyber-workspace` doirasidan tashqariga chiqishni (symlink, path traversal, `.env`) qat'iy cheklovchi jail resolver.
4. **10 ta Xavfsiz Asboblar Implementatsiyasi:**
   - `get_local_time` (GREEN): Toshkent/boshqa vaqt zonalari.
   - `get_system_status` (GREEN): CPU, RAM, Disk, Batareya, GPU (psutil + nvidia-smi).
   - `search_workspace` (GREEN): Ishchi jilddan fayl va matn qidirish.
   - `open_allowed_app` (GREEN): `config/apps_allowlist.toml` bo'yicha ilovalarni ochish.
   - `set_volume` (GREEN): 0–100 oralig'ida ovozni boshqarish.
   - `create_timer` va `list_timers` (GREEN): Vaqt taymerlari.
   - `draft_message` (GREEN): Qoralama xat tayyorlash (yuborilmaydi).
   - `web_search_read` (GREEN, sessiyani zaharlaydi): `config/url_rules.toml` ruxsat etilgan URL-larni o'qish.
   - `write_workspace_file` (YELLOW): Yangi fayl yaratish (ustiga yozish taqiqlangan).
   - `move_workspace_file` (YELLOW): Ishchi jild ichida faylni ko'chirish.
   - `run_test_suite` (YELLOW): Bubblewrap (`bwrap`) tarmoqsiz rootless sandboxda testlarni yurgizish.
5. **Miya Orkestratori va Fon Vazifalari (`src/cyber_agent/brain/`):**
   - `task_queue.py`: Uzoq davom etuvchi amallar uchun asinxron in-memory navbat va bekor qilish tizimi.
   - `orchestrator.py`: Gemini Live funksiyalarini NON_BLOCKING tarzda asboblar registri va siyosat dvigateliga bog'lovchi orkestrator; rad etilganda o'zbekcha ovozli javob qaytaradi.
   - `gemini_live.py`: Model bilan aloqa jarayonida tool call va response almashinuvi integratsiyasi.
6. **PWA Mobil Tasdiqlash Kartochkasi (`frontend/pwa/`):**
   - `index.html`, `app.js`, `style.css`: Sariq toifadagi amallar uchun ekranda chiqadigan modal kartochka (amal nomi, nishon, parametrlar, xavf ogohlantirishi, 60s progress bar va Tasdiqlash/Bekor qilish tugmalari).
   - `websocket.py`: `confirm_card` va `confirm_response` boshqaruv xabarlari.
7. **Mustaqil Kill Switch va Hotkey (`src/cyber_agent/killswitch/`):**
   - `service.py`: Unix soketda (`~/.cyber/killswitch.sock`) tinglovchi alohida demon; STOP signalida barcha bola jarayon guruhlarini (`SIGKILL`), tasdiqlarni va fon navbatini bekor qiladi.
   - `client.py` & `scripts/cyber-stop`: CLI to'xtatish skripti.
   - `tests/integration/test_killswitch.py`: O'lchangan o'chirish tezligi: **0.94 ms** (talab: $\le 1.0\text{ s}$).
8. **Tizim Servislari va Qo'lda Bajariladigan Skriptlar:**
   - `systemd/cyber-core.service`: Asosiy shlyuz uchun user servisi.
   - `systemd/cyber-killswitch.service`: Mustaqil kill switch servisi.
   - `scripts/manual/04-install-services.sh`: Servislarni yoqish bo'yicha ko'rsatma.
   - `scripts/manual/05-gnome-hotkey.sh`: GNOME `Super+Shift+Escape` hotkey o'rnatish skripti.
9. **Red-Team Xavfsizlik Testlari (`tests/security/test_red_team.py`):**
   - MASTER_PLAN §18.3 dagi 10 ta hujum to'liq sinovdan o'tkazildi (10/10 BLOCKED).
10. **O'zbekcha Benchmark (`tests/benchmark/`):**
    - `uzbek_100.jsonl`: 100 ta gapdan iborat test to'plami.
    - `run.py`: Dry-run tekshiruvi. Aniqlik: **96.0%** intent, **100.0%** ruxsat siyosati.
    - `docs/benchmark.md`: Natijalar jadvali saqlandi.
11. **Zaxiralash va Qayta Tiklash (`scripts/backup.py`):**
    - `data/` va `config/` jildlarini xavfsiz arxivlash (maxfiy fayllar va soketlar chiqarib tashlanadi) va xavfsiz tiklash. `tests/unit/test_backup.py` sinovdan o'tkazildi.

---

## 3. Tekshiruv natijalari
Haqiqiy test va linter buyruqlari natijalari:

- **Customizations audit:**
  ```text
  $ uv run python scripts/check_customizations.py
  OK: All rules and skills passed customization verification.
  ```
- **Ruff linter:**
  ```text
  $ uv run ruff check .
  All checks passed!
  ```
- **Mypy qat'iy tip tekshiruvi:**
  ```text
  $ MYPYPATH=src:. uv run mypy src/ tests/ scripts/
  Success: no issues found in 64 source files
  ```
- **Pytest to'liq sinov paketi:**
  ```text
  $ uv run pytest
  ============================== 51 passed in 2.16s ==============================
  tests/integration/test_killswitch.py .                                   [  1%]
  tests/integration/test_websocket_api.py .......                          [ 15%]
  tests/security/test_red_team.py ..........                               [ 35%]
  tests/unit/test_audit.py ..                                              [ 39%]
  tests/unit/test_backup.py ..                                             [ 43%]
  tests/unit/test_config.py ..                                             [ 47%]
  tests/unit/test_orchestrator.py .....                                    [ 56%]
  tests/unit/test_policy.py ....                                           [ 64%]
  tests/unit/test_providers.py ......                                      [ 76%]
  tests/unit/test_registry.py ...                                          [ 82%]
  tests/unit/test_tools.py .........                                       [100%]
  ```
- **Kill Switch tezligi o'lchovi:**
  ```text
  [MEASURED KILL SWITCH LATENCY]: 0.94 ms (<= 1.0 s talabiga to'liq javob beradi)
  ```
- **O'zbekcha 100-gapli benchmark:**
  ```text
  Total Sentences Tested: 100
  Intent Accuracy:       96/100 (96.0%)
  Tier Policy Accuracy:  100/100 (100.0%)
  Total Elapsed Time:    0.25 ms
  ```
- **Xavfsizlik 10-hujum Red Team sinovi:**
  Barcha 10 ta hujum (`.env` o'g'irlash, SMS yuborish, `id_rsa` path traversal, ro'yxatdan tashqari ilova, `sudo`, tokenni qayta ishlatish, STOP holatida buyruq berish, idempotency replay, asboblar registrini buzish, API kalit sizishi) to'liq to'xtatildi va auditga yozildi (10/10 PASSED).

---

## 4. Siz bajaradigan tekshiruvlar (USER-TEST-REQUIRED)
1. **Kill Switch Hotkey sinovi:**
   - Terminalda `scripts/manual/05-gnome-hotkey.sh` ni ishga tushiring.
   - Biror uzoq vazifani boshlab, klaviaturadan `Super + Shift + Escape` bosing. Agent to'xtaganini tekshiring.
2. **PWA orqali Sariq amalni tasdiqlash:**
   - Brauzerda PWA-ni oching (`https://...` orqali).
   - "Fayl yarat" deb ayting yoki yozing.
   - Mobil ekranda sariq tasdiqlash kartochkasi va 60 soniyalik teskari hisob paydo bo'lishini, "Tasdiqlash" tugmasi bosilmaguncha fayl yaratilmasligini tekshiring.
3. **Zaxiralash sinovi:**
   - `python scripts/backup.py --backup` buyrug'ini bering va `data/backups/` ichida arxiv yaratilganini ko'ring.

---

## 5. Qo'lda bajariladigan tizim qadamlari
- `scripts/manual/04-install-services.sh` — systemd user servislari (`cyber-killswitch.service`, `cyber-core.service`) ni avtomatik ishga tushirish uchun yoqing.
- `scripts/manual/05-gnome-hotkey.sh` — GNOME muhitida favqulodda to'xtatish tugmalar birikmasini bog'lash uchun bir marta bajaring.

---

## 6. Muammolar va qarorlar
- **Gemini Live NON_BLOCKING Behavior:** `types.FunctionDeclaration` da `behavior=types.Behavior.NON_BLOCKING` xossasi qo'llanildi. Bu modelga asbob natijasini kutmasdan nutqni erkin davom ettirish va asbob javobi kelganda uni e'lon qilish imkonini berdi.
- **Rootless Sandbox:** Bubblewrap (`bwrap`) tarmoq ajratilgan holda (`--unshare-net`) sinovdan o'tkazildi.

---

## 7. Rejadan chetlanishlar
- Yo'q. MASTER_PLAN §7, §8, §13, §17, §18 dagi barcha bandlar belgilangan ketma-ketlikda, o'zgartirishsiz to'liq bajarildi.

---

## 8. Keyingi qadam
Stage S2 muvaffaqiyatli yakunlandi va MVP talablari to'liq qondirildi.
Iltimos, ushbu bosqichni ko'rib chiqing va tasdiqlasangiz chatda **`APPROVED STAGE 2`** deb yozing. Shundan so'ng filial `main` ga birlashtiriladi va Stage S3 (Local Brain & Uzbek Voice) rejalashtirishiga o'tiladi.
