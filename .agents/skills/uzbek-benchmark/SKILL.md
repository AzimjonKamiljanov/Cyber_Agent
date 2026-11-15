---
name: uzbek-benchmark
description: Builds and runs the 100-sentence Uzbek voice/command benchmark and produces the results table. Use when creating tests/benchmark files or comparing voice modes and STT/TTS models.
---
# Uzbek benchmark
- Schema per line: id, category, text_uz, expected_intent, expected_args, expected_permission_tier, audio_file (optional).
- Categories and counts: 30 simple commands, 20 date/time/number, 20 Uzbek+English IT, 15 Russian words/names/places, 15 long multi-step. Dangerous lines run dry-run only.
- Metrics: intent accuracy, argument accuracy, tier accuracy, WER (local STT, normalized), latency P50/P95, TTS score 1–5 (owner-rated), recovery time. At least 3 repeats.
- Output `docs/benchmark.md` with one table per mode. Mark human-rated cells `USER-RATED`.
- Do not tune the benchmark to pass; report real numbers.
