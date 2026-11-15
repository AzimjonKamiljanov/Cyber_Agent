"""Online TTS fallback provider using edge-tts (uz-UZ-SardorNeural / MadinaNeural).

STRICT INVARIANT:
Never called if Privacy Mode is active or when offline.
Produces PCM16 mono 24 kHz audio chunks matching WebSocket gateway specs.
"""

from __future__ import annotations

import io
import logging
from collections.abc import AsyncIterator

import av
import edge_tts

from cyber_agent.config import get_settings

logger = logging.getLogger(__name__)


def mp3_chunk_to_pcm16(mp3_bytes: bytes, target_sr: int = 24000) -> bytes:
    """Decode MP3 bytes and resample to PCM16 mono at target_sr."""
    if not mp3_bytes:
        return b""
    try:
        container = av.open(io.BytesIO(mp3_bytes))
        assert isinstance(container, av.container.InputContainer)
        resampler = av.AudioResampler(format="s16", layout="mono", rate=target_sr)
        out_chunks: list[bytes] = []
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                out_chunks.append(bytes(resampled.planes[0]))
        return b"".join(out_chunks)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to decode MP3 chunk to PCM: %s", e)
        return b""


class EdgeTTSProvider:
    """Online Uzbek TTS provider via Microsoft Edge Neural voice."""

    def __init__(self, voice: str | None = None) -> None:
        settings = get_settings()
        self.voice = voice or settings.cyber_edge_tts_voice

    async def stream_audio(self, text: str) -> AsyncIterator[bytes]:
        """Stream synthesized audio as PCM16 24 kHz mono bytes."""
        settings = get_settings()
        if settings.cyber_privacy_mode:
            raise PermissionError(
                "Privacy Mode violation: edge-tts is an online service and is strictly forbidden in Privacy Mode."
            )

        if not text.strip():
            return

        communicator = edge_tts.Communicate(text, self.voice)
        buffer = bytearray()

        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                buffer.extend(chunk["data"])
                # Yield when buffer reaches reasonable chunk size (~8KB mp3)
                if len(buffer) >= 8192:
                    pcm = mp3_chunk_to_pcm16(bytes(buffer), 24000)
                    buffer.clear()
                    if pcm:
                        yield pcm

        if buffer:
            pcm = mp3_chunk_to_pcm16(bytes(buffer), 24000)
            if pcm:
                yield pcm

    async def synthesize_to_pcm(self, text: str) -> bytes:
        """Synthesize entire text and return PCM16 24 kHz mono bytes."""
        chunks: list[bytes] = []
        async for chunk in self.stream_audio(text):
            chunks.append(chunk)
        return b"".join(chunks)
