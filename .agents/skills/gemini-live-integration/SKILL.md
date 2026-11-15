---
name: gemini-live-integration
description: Guides implementation of the Gemini 3.8 Live voice provider with transcription, compression, resumption, GoAway handling, barge-in and non-blocking tools. Use when working on providers/gemini_live.py or the voice gateway.
---
# Gemini Live provider checklist
1. Introspect installed `google-genai` for exact config class/field names; note versions in `docs/decisions/`.
2. Config: audio response, input+output transcription, compression, resumption, Uzbek persona (MASTER_PLAN Appendix B).
3. Reconnect loop: on GoAway/close → reconnect with last resumption handle; cap retries; fail-closed to Mode C on quota errors.
4. Barge-in: on PTT press or user speech → flush playback queue and interrupt generation.
5. Tools: declare NON_BLOCKING; handler returns immediately; results announced later; all calls pass the policy engine.
6. Metrics: log P50/P95 from end-of-speech to first audio byte (no content in logs).
