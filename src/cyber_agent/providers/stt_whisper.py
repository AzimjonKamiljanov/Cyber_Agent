"""Local Speech-to-Text provider powered by faster-whisper on CUDA/CPU.

Enforces:
- Automatic fallback from CUDA to CPU if memory fails.
- Built-in Silero VAD filter to reduce silence processing.
- Strict Uzbek Latin script output normalization.
- Memory unloading support to respect the 8 GB VRAM budget.
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Any

import numpy as np

from cyber_agent.config import get_settings
from cyber_agent.providers.uzbek_script import cyrillic_to_latin

logger = logging.getLogger(__name__)


class WhisperSTTProvider:
    """faster-whisper inference wrapper for Uzbek speech-to-text."""

    def __init__(
        self,
        model_id: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        vad_filter: bool = True,
    ) -> None:
        settings = get_settings()
        self.model_id = model_id or settings.cyber_stt_model
        self.preferred_device = device or settings.cyber_stt_device
        self.preferred_compute_type = compute_type or settings.cyber_stt_compute_type
        self.vad_filter = vad_filter

        self._model: Any = None
        self._active_device: str = "none"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load faster-whisper model into GPU or CPU memory."""
        if self._model is not None:
            return

        import faster_whisper

        target_device = self.preferred_device
        target_compute = self.preferred_compute_type

        # Verify CUDA capability
        if target_device == "cuda":
            import ctranslate2

            if ctranslate2.get_cuda_device_count() == 0:
                logger.warning("CUDA requested but no CUDA device found. Falling back to CPU.")
                target_device = "cpu"
                target_compute = "int8"

        try:
            logger.info(
                "Loading faster-whisper model '%s' on %s (%s)...",
                self.model_id,
                target_device,
                target_compute,
            )
            self._model = faster_whisper.WhisperModel(
                self.model_id,
                device=target_device,
                compute_type=target_compute,
            )
            self._active_device = target_device
            logger.info("faster-whisper model loaded successfully on %s.", target_device)
        except Exception as exc:
            if target_device == "cuda":
                logger.warning(
                    "Failed to load on CUDA (%s). Retrying with CPU int8...", exc
                )
                self._model = faster_whisper.WhisperModel(
                    self.model_id,
                    device="cpu",
                    compute_type="int8",
                )
                self._active_device = "cpu"
            else:
                raise

    def unload(self) -> None:
        """Unload model and free GPU VRAM."""
        if self._model is not None:
            logger.info("Unloading faster-whisper model from memory...")
            del self._model
            self._model = None
            self._active_device = "none"
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def transcribe_audio_array(self, audio: np.ndarray, language: str = "uz") -> str:
        """Transcribe normalized float32 audio array (16 kHz mono)."""
        if self._model is None:
            self.load()

        segments, _info = self._model.transcribe(
            audio,
            language=language,
            task="transcribe",
            vad_filter=self.vad_filter,
            vad_parameters={"min_silence_duration_ms": 400},
            beam_size=5,
        )

        texts = [seg.text.strip() for seg in segments if seg.text.strip()]
        raw_text = " ".join(texts)
        # Normalize strictly to Latin script
        return cyrillic_to_latin(raw_text)

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe 16-bit signed PCM mono audio bytes."""
        if not pcm_bytes:
            return ""

        # Convert int16 bytes to normalized float32 [-1.0, 1.0]
        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        if len(audio_int16) == 0:
            return ""
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        return self.transcribe_audio_array(audio_float32)

    def transcribe_file(self, audio_path: str | Path, language: str = "uz") -> str:
        """Transcribe audio from file path (WAV/MP3/OGG)."""
        import av

        path_str = str(audio_path)
        container = av.open(path_str)
        resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
        frames_data: list[np.ndarray] = []
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                frames_data.append(resampled.to_ndarray().flatten())

        if not frames_data:
            return ""

        audio_float32 = np.concatenate(frames_data)
        return self.transcribe_audio_array(audio_float32, language=language)
