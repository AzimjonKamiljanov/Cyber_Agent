#!/usr/bin/env python3
"""Interactive microphone audio recording tool for Uzbek 100-sentence benchmark.

Records audio in 16 kHz 16-bit mono WAV format for evaluating Whisper STT accuracy (WER/CER).
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

BENCHMARK_FILE = Path(__file__).resolve().parent.parent / "tests" / "benchmark" / "uzbek_100.jsonl"
AUDIO_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmark_audio"


def record_sentence(text_uz: str, out_path: Path, sample_rate: int = 16000) -> None:
    print(f"\n[MATN]: \"{text_uz}\"")
    input("Yozib olishni boshlash uchun [ENTER] ni bosing...")

    frames: list[np.ndarray] = []
    is_recording = True

    def callback(indata: np.ndarray, frame_count: int, time_info: dict[str, float], status: sd.CallbackFlags) -> None:
        if is_recording:
            frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        callback=callback,
    )

    with stream:
        input("Gapiring... Yozib olishni to'xtatish uchun yana [ENTER] ni bosing...")
        is_recording = False

    if not frames:
        print("Xatolik: Hech qanday audio yozilmadi.")
        return

    audio_data = np.concatenate(frames, axis=0)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

    duration = len(audio_data) / sample_rate
    print(f"Saqlandi: {out_path} ({duration:.2f} soniya)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Uzbek Benchmark Audio Recorder")
    parser.add_argument("--start", type=int, default=1, help="Sentence ID to start from (1-100)")
    parser.add_argument("--count", type=int, default=10, help="Number of sentences to record")
    args = parser.parse_args()

    if not BENCHMARK_FILE.exists():
        print(f"Fayl topilmadi: {BENCHMARK_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(BENCHMARK_FILE, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]

    selected = [item for item in items if args.start <= item["id"] < args.start + args.count]
    print(f"Jami {len(selected)} ta jumla yozib olinadi.")

    for item in selected:
        out_path = AUDIO_OUT_DIR / f"uz_{item['id']:03d}.wav"
        record_sentence(item["text_uz"], out_path)

    print("\nBarcha tanlangan jadvallar yozib olindi!")


if __name__ == "__main__":
    main()
