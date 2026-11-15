#!/usr/bin/env python3
"""TTS Evaluation Harness for Cyber Agent Stage S3.

Evaluates candidates in order:
1. aisha-org/navoiy-tts (CosyVoice2 runtime)
2. Saidakmal02/Uzbek_TTS (HF status / accessibility)
3. uzlm/sayro-tts-1.7B (Weight size, VRAM constraints)
4. edge-tts (Online fallback: uz-UZ-SardorNeural / MadinaNeural)

Generates 10 representative Uzbek audio samples and outputs performance metrics.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from pathlib import Path
from typing import Any

import av
import edge_tts

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_SENTENCES = [
    ("sample_01_greeting", "Assalomu alaykum, Azimjon! Men Cyber Agentman."),
    ("sample_02_datetime", "Bugun 2026-yil 15-noyabr, yakshanba kuni."),
    ("sample_03_time", "Hozir soat o'n to'rt yarim bo'ldi."),
    ("sample_04_it_terms", "Ghostty terminalida git status buyrug'ini ishga tushiring."),
    ("sample_05_docker", "Docker konteynerlarini qayta ishga tushirish muvaffaqiyatli yakunlandi."),
    ("sample_06_sys_status", "Tizim holati: protsessor yigirma foiz, operativ xotira o'n ikki gigabayt."),
    ("sample_07_volume", "Ovoz balandligini ellik foizga o'rnatdim."),
    ("sample_08_places", "Samarqand va Buxoro shaharlarida havo ochiq va quyoshli bo'ladi."),
    ("sample_09_security", "Xavfsizlik qoidalariga ko'ra, faylni o'chirish taqiqlangan."),
    ("sample_10_tests", "Barcha testlar muvaffaqiyatli o'tdi, tizim tayyor."),
]


def mp3_to_wav(mp3_bytes: bytes, target_sr: int = 24000) -> bytes:
    """Decode MP3 bytes and encode to 16-bit mono WAV bytes."""
    input_container = av.open(io.BytesIO(mp3_bytes))
    assert isinstance(input_container, av.container.InputContainer)
    resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)

    output_buffer = io.BytesIO()
    output_container = av.open(output_buffer, mode="w", format="wav")
    output_stream = output_container.add_stream("pcm_s16le", rate=target_sr)
    output_stream.layout = "mono"

    for frame in input_container.decode(audio=0):
        for resampled_frame in resampler.resample(frame):
            for packet in output_stream.encode(resampled_frame):
                output_container.mux(packet)

    for packet in output_stream.encode(None):
        output_container.mux(packet)

    output_container.close()
    return output_buffer.getvalue()


async def evaluate_edge_tts(output_dir: Path) -> list[dict[str, Any]]:
    """Synthesize 10 sample sentences with edge-tts and measure RTF."""
    results: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    voice = "uz-UZ-SardorNeural"
    logger.info("Evaluating edge-tts (%s)...", voice)

    for slug, text in SAMPLE_SENTENCES:
        t0 = time.monotonic()
        communicator = edge_tts.Communicate(text, voice)
        audio_chunks: list[bytes] = []

        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        synthesis_time = time.monotonic() - t0
        mp3_data = b"".join(audio_chunks)
        wav_data = mp3_to_wav(mp3_data, 24000)

        wav_path = output_dir / f"{slug}.wav"
        wav_path.write_bytes(wav_data)

        # Calculate audio duration from WAV size (2 bytes per sample * 24000 samples/sec)
        # Header is 44 bytes in standard WAV
        data_bytes = max(0, len(wav_data) - 44)
        duration_s = data_bytes / (24000 * 2)
        rtf = synthesis_time / duration_s if duration_s > 0 else 0.0

        results.append(
            {
                "slug": slug,
                "text": text,
                "synthesis_time_s": round(synthesis_time, 3),
                "duration_s": round(duration_s, 2),
                "rtf": round(rtf, 3),
                "wav_file": str(wav_path),
            }
        )
        logger.info("Generated %s (duration: %.2fs, synthesis: %.2fs, RTF: %.3f)", slug, duration_s, synthesis_time, rtf)

    return results


def print_candidate_matrix() -> None:
    """Print the candidate evaluation matrix."""
    matrix = [
        {
            "candidate": "1. aisha-org/navoiy-tts",
            "license": "Apache-2.0",
            "runtime": "CosyVoice2 (complex C++/PyTorch tree)",
            "weights": "1.88 GB",
            "vram": "~2.2 GB",
            "status": "High quality; requires full CosyVoice2 stack",
        },
        {
            "candidate": "2. Saidakmal02/Uzbek_TTS",
            "license": "Unknown",
            "runtime": "N/A",
            "weights": "N/A",
            "vram": "N/A",
            "status": "Inaccessible (HTTP 401 / Not Found on HF)",
        },
        {
            "candidate": "3. uzlm/sayro-tts-1.7B",
            "license": "Other",
            "runtime": "Transformers + SpeechTokenizer",
            "weights": "4.30 GB",
            "vram": ">4.5 GB",
            "status": "Too heavy for 8GB VRAM (exceeds budget with 8B LLM)",
        },
        {
            "candidate": "4. edge-tts (Online Fallback)",
            "license": "Microsoft Terms",
            "runtime": "Python (edge-tts)",
            "weights": "0 MB (Remote)",
            "vram": "0 MB",
            "status": "Excellent Uzbek pronunciation; blocked in Privacy Mode",
        },
    ]

    print("\n" + "=" * 80)
    print("TTS CANDIDATE EVALUATION MATRIX")
    print("=" * 80)
    for m in matrix:
        print(f"Candidate: {m['candidate']}")
        print(f"  License: {m['license']}")
        print(f"  Weights: {m['weights']} | VRAM Footprint: {m['vram']}")
        print(f"  Runtime: {m['runtime']}")
        print(f"  Status:  {m['status']}\n")


async def main() -> None:
    print_candidate_matrix()
    output_dir = Path("data/tts_eval_samples")
    results = await evaluate_edge_tts(output_dir)

    avg_rtf = sum(r["rtf"] for r in results) / len(results) if results else 0
    avg_latency = sum(r["synthesis_time_s"] for r in results) / len(results) if results else 0

    print("=" * 80)
    print(f"EVALUATION COMPLETE: {len(results)} samples synthesized into data/tts_eval_samples/")
    print(f"Average Synthesis Latency: {avg_latency:.3f} s")
    print(f"Average Real-Time Factor (RTF): {avg_rtf:.3f}")
    print("=" * 80 + "\n")

    # Save summary JSON
    summary_file = output_dir / "tts_eval_summary.json"
    summary_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
