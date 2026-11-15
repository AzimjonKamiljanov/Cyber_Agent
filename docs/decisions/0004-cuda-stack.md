# Decision Record 0004: CUDA Stack & Local Runtime for RTX 5070 Laptop (Blackwell)

## Context
Cyber Agent requires local, offline-capable speech-to-text (STT), large language model (LLM), and text-to-speech (TTS) inference running directly on the owner's laptop (Legion Pro 5) without external cloud dependencies.
The laptop is equipped with an NVIDIA GeForce RTX 5070 Laptop GPU running driver 595.99.02 with CUDA 13.2 and 8151 MiB (~8.0 GB) total VRAM.

## Hardware & Environment Audit Findings
- **GPU:** NVIDIA GeForce RTX 5070 Laptop GPU
- **VRAM Total:** 8151 MiB (verified via `nvidia-smi`)
- **Driver Version:** 595.99.02
- **CUDA Runtime:** 13.2
- **Architecture:** NVIDIA Blackwell (Compute Capability 12.0 / SM_120)
- **Host OS:** Ubuntu 26.04.1 LTS (x86_64, Linux 7.0.0-43-generic)

## Evaluated Packages & Compatibility Matrix

### 1. CTranslate2 & faster-whisper
- **Installed Packages:**
  - `ctranslate2==4.9.0`
  - `faster-whisper==1.2.1`
  - `onnxruntime==1.32.0`
- **CUDA Verification:**
  - `ctranslate2.get_cuda_device_count()`: `1`
  - CUDA execution: Tested and verified directly on GPU with `WhisperModel('tiny', device='cuda', compute_type='float16')`.
  - Supported CUDA compute types: `float16`, `int8_float16`, `bfloat16`, `float32`, `int8`, `int8_bfloat16`.
  - Measured VRAM with tiny model loaded: 253 MiB / 8151 MiB.

### 2. Local Uzbek STT Candidates & Licenses
| Candidate | Repository | License | Format | Status / Recommendation |
|---|---|---|---|---|
| 1. Mannon Uzbek Whisper | `Mannon/whisper-medium-uzbek` | Apache-2.0 | Whisper medium | Permissive, tested in benchmark |
| 2. BuzzASR Uzbek | `BuzzASR/uzbek` | MIT | Whisper medium | Permissive, alternative |
| 3. Rubai STT v2 | `islomov/rubaistt_v2_medium` | Apache-2.0 | Whisper medium | Permissive, tuned on Uzbek speech |
| 4. Whisper Large v3 Turbo | `openai/whisper-large-v3-turbo` | MIT | Large Turbo | Multilingual fallback with fast inference |

### 3. Local LLM Runtime (Ollama)
- **Engine:** Ollama HTTP REST API on `http://127.0.0.1:11434`
- **Model Target:** `qwen3:8b` (or `qwen2.5:7b-instruct-q4_K_M` as immediate production equivalent)
- **Quantization:** Q4_K_M (~4.7 GB VRAM footprint)
- **Concurrency:** 1 parallel request (`OLLAMA_NUM_PARALLEL=1`) to prevent VRAM spikes.

### 4. Uzbek TTS Candidates & Licenses
| Candidate | Repository / Engine | License | VRAM Footprint | Status |
|---|---|---|---|---|
| 1. Lison Navoiy TTS | `aisha-org/navoiy-tts` | Apache-2.0 | ~2.2 GB (CosyVoice2-0.5B base) | High expressive quality; requires CosyVoice2 runtime |
| 2. Uzbek_TTS | `Saidakmal02/Uzbek_TTS` | Private / 401 | N/A | Inaccessible (repo private or removed) |
| 3. Sayro TTS 1.7B | `uzlm/sayro-tts-1.7B` | Other | ~4.3 GB weights | Too heavy to co-exist with 8B LLM in 8GB VRAM |
| 4. SpeechT5 Uzbek | `Beehzod/speechT5_tts_uzbek` | MIT | ~350 MB | Lightweight local fallback |
| 5. Edge TTS (Online Fallback) | `uz-UZ-SardorNeural` / `MadinaNeural` | Microsoft TOS | 0 MB (Remote) | Online fallback only; strictly blocked in Privacy Mode |

## VRAM Budget & Offloading Strategy
The total VRAM is strictly bounded at 8151 MiB:
- **Baseline OS/Desktop:** ~50 MiB
- **STT (Whisper Medium float16):** ~1500 MiB
- **LLM (Ollama Qwen 7B/8B Q4):** ~4700 MiB
- **Sum (STT + LLM):** ~6250 MiB (Within 8151 MiB budget!)
- **Remaining headroom:** ~1900 MiB

If a heavy TTS model (>2 GB) is loaded concurrently, total VRAM exceeds the 8 GB limit and triggers CUDA OOM.
**Strategy Decision:**
1. Default local cascade uses `faster-whisper` (medium, float16) + Ollama Q4.
2. For TTS in Mode C (Local): Use lightweight local TTS or sequential execution where STT memory can be freed before TTS synthesis if needed.
3. In Mode B (Cascade with cloud): Gemini text is used in cloud, leaving full 8 GB VRAM for local STT + local TTS.
4. Edge-TTS serves as high-quality online fallback for Mode B when internet is available and content is non-private.

## Manual Script
Heavy model downloads and model pulling are codified into `scripts/manual/06-download-models.sh` for the owner to execute.
