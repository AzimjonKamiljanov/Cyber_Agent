# Bosqich hisoboti: S1 — Ovozli yadro (Voice Core: Gemini 3.8 Live + PWA)

## 1. Xulosa
S1 bosqichi to'liq va muvaffaqiyatli yakunlandi. Tier T1 ("Talk") talablari asosida past kechikishli (low-latency) ovozli shlyuz yaratildi. O'rnatilgan `google-genai==3.3.0` kutubxonasining real Live API imkoniyatlari to'liq tahlil qilinib, O'zbekcha persona, avtomatik transkripsiya, kontekst kompressiyasi, sessiyani tiklash (resumption) va GoAway signali qayta ulanishi bilan `GeminiLiveProvider` ishlab chiqildi. Shuningdek, `127.0.0.1:8000` ga bog'langan FastAPI WebSocket shlyuzi, deterministik testlar uchun `MockLiveProvider`, terminal PoC utility hamda Poco F6 Pro uchun AudioWorklet va Push-to-Talk xususiyatlariga ega vanilla PWA yaratildi. Barcha 14 ta avtomatlashtirilgan unit va integratsion testlar 100% muvaffaqiyatli o'tdi.

## 2. Nima qilindi
- **Bog'liqliklar va SDK Introspeksiyasi:**
  - `pyproject.toml` ga faqat §5.2 da ruxsat etilgan kutubxonalar (`fastapi`, `uvicorn[standard]`, `pydantic-settings`, `google-genai`, `numpy`, `sounddevice`, `websockets`) qo'shildi va `uv.lock` yangilandi.
  - `google-genai==3.3.0` introspeksiya qilinib, [docs/decisions/0001-live-sdk-notes.md](file:///home/cyber/Cyber_Agent/docs/decisions/0001-live-sdk-notes.md) hujjati yozildi.
- **Konfiguratsiya va Provayderlar:**
  - `src/cyber_agent/config.py`: maxfiy kalitlarni `***` bilan niqoblovchi Pydantic-settings sozlamalari.
  - `src/cyber_agent/providers/base.py`: hodisalar (`AudioOutEvent`, `TranscriptInEvent`, `TranscriptOutEvent`, `StatusEvent`, `ErrorEvent`) va `VoiceProvider` interfeysi.
  - `src/cyber_agent/providers/gemini_live.py`: Gemini 3.8 Live bilan 16 kHz kiruvchi va 24 kHz chiquvchi audio oqimi, Uzbek persona (Appendix B), GoAway qayta ulanishi, `QuotaExhaustedError` nol-xarajat himoyasi, barge-in va P50/P95 kechikish hisoblagichi. Hech qanday tool kiritilmadi (No-tools invariant).
  - `src/cyber_agent/providers/mock_live.py`: deterministik test provayderi.
- **Terminal PoC:**
  - `scripts/live_terminal_test.py`: noutbuk mikrofon va karnayi orqali Enter-PTT bilan 5 daqiqalik jonli muloqot utilitasi.
- **FastAPI Shlyuzi va WebSocket:**
  - `src/cyber_agent/api/routes.py` (`GET /healthz`) va `src/cyber_agent/api/websocket.py` (`/ws/voice`).
  - Xavfsizlik: faqat `127.0.0.1` ga ulanadi, `CYBER_PAIRING_TOKEN` va Origin tekshiruvi, bitta faol sessiya qoidasi, kadr o'lchami cheklovi, favqulodda ichki STOP (barcha oqimlarni darhol to'xtatish va tozalash).
  - `src/cyber_agent/main.py`: statik PWA fayllarini ulash va serverni ishga tushirish.
- **Progressive Web App (PWA):**
  - `frontend/pwa/`: `index.html`, `style.css`, `app.js`, `audio-processor.js` (AudioWorklet 16 kHz PCM16), `manifest.webmanifest`, `sw.js`.
  - Push-to-Talk tugmasi, mikrofon apparat diagnostikasi (`getSettings()`: echoCancellation, noiseSuppression, autoGainControl), 24 kHz o'ynatish navbati va PTT bosilganda yoki STOP chaqirilganda bir zumda navbatni tozalash (flush).
- **Tarmoq va Transport qarori:**
  - `docs/setup-tailscale.md` va `scripts/manual/03-tailscale-serve.sh` (Tailscale Serve HTTPS qo'llanmasi).
  - `docs/decisions/0003-transport.md`: FastAPI WebSocket vs LiveKit solishtirma mezoni (qaror xulosasi qismi foydalanuvchi natijalari uchun bo'sh qoldirildi).
- **Testlar:**
  - `tests/unit/test_config.py`, `tests/unit/test_providers.py`, `tests/integration/test_websocket_api.py`.

## 3. Tekshiruv natijalari
- **Avtomatik testlar (Pytest):**
  ```text
  tests/integration/test_websocket_api.py::test_healthz PASSED             [  7%]
  tests/integration/test_websocket_api.py::test_socket_binding PASSED      [ 14%]
  tests/integration/test_websocket_api.py::test_bad_token_rejected PASSED  [ 21%]
  tests/integration/test_websocket_api.py::test_wrong_origin_rejected PASSED [ 28%]
  tests/integration/test_websocket_api.py::test_audio_streaming_and_transcripts PASSED [ 35%]
  tests/integration/test_websocket_api.py::test_barge_in_and_stop PASSED   [ 42%]
  tests/unit/test_config.py::test_settings_secret_masking PASSED           [ 50%]
  tests/unit/test_config.py::test_settings_default_values PASSED           [ 57%]
  tests/unit/test_providers.py::test_mock_live_normal_flow PASSED          [ 64%]
  tests/unit/test_providers.py::test_mock_live_interrupt_barge_in PASSED   [ 71%]
  tests/unit/test_providers.py::test_mock_live_goaway_handling PASSED      [ 78%]
  tests/unit/test_providers.py::test_mock_live_quota_exhausted PASSED      [ 85%]
  tests/unit/test_providers.py::test_session_closed_error PASSED           [ 92%]
  tests/unit/test_providers.py::test_is_quota_error_detection PASSED       [100%]

  ============================== 14 passed in 0.40s ==============================
  ```
- **Linter va Type-checker:**
  ```text
  $ .venv/bin/ruff check .
  All checks passed!
  $ .venv/bin/mypy src/ tests/ scripts/
  Success: no issues found in 27 source files
  $ python3 scripts/check_customizations.py
  OK: All rules and skills passed customization verification.
  ```
- **Sirlar va Git skani:** Git diffda hech qanday API kalit yoki token saqlanmaganligi tasdiqlandi.

## 4. Siz bajaradigan tekshiruvlar (USER-TEST-REQUIRED)
1. **Terminalda jonli sinov (5 daqiqalik o'zbekcha suhbat):**
   ```bash
   uv run python scripts/live_terminal_test.py
   # Agar .env da kalit bo'lmasa, --mock flag bilan ham tekshirish mumkin
   ```
2. **Tailscale Serve va Telefon (PWA) sinovi:**
   - Serverni ishga tushiring: `uv run python -m cyber_agent.main`
   - Boshqa oynada `scripts/manual/03-tailscale-serve.sh` ni ishga tushiring.
   - Poco F6 Pro telefoningizda Chrome brauzerida chiqarilgan `https://<laptop-tailnet-name>.ts.net` manzilini oching.
   - `.env` dagi `CYBER_PAIRING_TOKEN` ni kiriting va Saqlash tugmasini bosing.
   - Huawei FreeArc quloqchinini ulab, Push-to-Talk orqali o'zbek tilida gaplashing.
   - Ekranda audio sozlamalari qiymatlarini (`echoCancellation`, `noiseSuppression`) va jonli transkripsiyani ko'ring; agent gapirayotganda tugmani bosib gapni bo'lish (barge-in) va qizil STOP tugmasi ishini tekshiring.
3. **Qaror qaydini to'ldirish:**
   - [docs/decisions/0003-transport.md](file:///home/cyber/Cyber_Agent/docs/decisions/0003-transport.md) dagi bo'sh katakchalarga o'lchangan kechikish va audio sifatiga oid xulosangizni yozib qo'ying.

## 5. Qo'lda bajariladigan tizim qadamlari
- `scripts/manual/03-tailscale-serve.sh` skriptini ko'rib chiqib, Tailscale Serve orqali port 8000 ni shaxsiy HTTPS sifatida ulash.

## 6. Muammolar va qarorlar
- Muammo bo'lmadi. `google-genai==3.3.0` da `types.LiveConnectConfig` va `session.send_realtime_input` to'liq kutilganidek ishladi va [docs/decisions/0001-live-sdk-notes.md](file:///home/cyber/Cyber_Agent/docs/decisions/0001-live-sdk-notes.md) ga kiritildi.

## 7. Rejadan chetlanishlar
- Yo'q. Barcha 11 ta vazifa va xavfsizlik talablari to'liq ketma-ketlikda bajarildi.

## 8. Keyingi qadam
O'z tekshiruvlaringizni o'tkazing va S1 bosqichini tasdiqlash hamda keyingi **Stage S2 (Safety Kernel, Tools v1 & MVP)** ga o'tish uchun **`APPROVED STAGE 1`** deb yozing.
