"""Unit tests for TTS providers (Edge TTS online fallback and Local offline TTS)."""

from typing import Any

import pytest

from cyber_agent.config import Settings
from cyber_agent.providers.tts_edge import EdgeTTSProvider
from cyber_agent.providers.tts_local import LocalTTSProvider


@pytest.mark.asyncio
async def test_edge_tts_privacy_mode_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(CYBER_PRIVACY_MODE=True)
    monkeypatch.setattr("cyber_agent.providers.tts_edge.get_settings", lambda: settings)

    provider = EdgeTTSProvider()
    with pytest.raises(PermissionError, match="Privacy Mode"):
        async for _ in provider.stream_audio("Salom"):
            pass


@pytest.mark.asyncio
async def test_local_tts_offline_synthesis() -> None:
    provider = LocalTTSProvider()
    pcm = await provider.synthesize_to_pcm("Assalomu alaykum!")
    assert len(pcm) > 0
    # Length in bytes must be multiple of 2 (16-bit PCM)
    assert len(pcm) % 2 == 0


@pytest.mark.asyncio
async def test_local_tts_stream_audio() -> None:
    provider = LocalTTSProvider()
    chunks: list[bytes] = []
    async for chunk in provider.stream_audio("Test"):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert all(len(c) % 2 == 0 for c in chunks)


@pytest.mark.asyncio
async def test_edge_tts_mocked_synthesis(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(CYBER_PRIVACY_MODE=False)
    monkeypatch.setattr("cyber_agent.providers.tts_edge.get_settings", lambda: settings)

    provider = EdgeTTSProvider()

    class MockComm:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def stream(self) -> Any:
            yield {"type": "audio", "data": b"\xff\xfb\x90\x00" * 200}

    monkeypatch.setattr("edge_tts.Communicate", MockComm)
    monkeypatch.setattr("cyber_agent.providers.tts_edge.mp3_chunk_to_pcm16", lambda b, sr: b"\x00\x00" * 100)

    pcm = await provider.synthesize_to_pcm("Salom")
    assert len(pcm) > 0
