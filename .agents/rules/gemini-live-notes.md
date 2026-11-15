---
trigger: model_decision
description: "Apply when writing or editing code that connects to the Gemini Live API, streams audio, or implements the voice gateway or providers/gemini_live.py."
---
# Gemini Live (`gemini-3.8-live`) implementation notes
- Model ID comes from config `CYBER_LIVE_MODEL` (default `gemini-3.8-live`). `gemini-3.1-flash-live-preview` is legacy.
- Do NOT send `thinking_level` / `thinking_config` for `gemini-3.8-live`. Do NOT set `enable_affective_dialog` or `proactive_audio:false`.
- Input audio: PCM16 little-endian mono, 16 kHz (any rate is resampled). Output: 24 kHz PCM16.
- Enable input and output audio transcription.
- Mandatory: context window compression, session resumption (store latest handle), GoAway handling with reconnect.
- Function calls default to async `NON_BLOCKING`: return a "started" status fast, speak the result later (`WHEN_IDLE` for non-urgent).
- `send_client_content(turn_complete=True)` interrupts generation (useful for barge-in).
- API key only on the server. Check exact SDK field names by introspecting the installed `google-genai`.
