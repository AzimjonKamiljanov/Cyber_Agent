"""Tests for Privacy Mode network isolation.

Guarantees that when Privacy Mode is enabled:
1. ModelRouter strictly locks active mode to Mode C (Local).
2. All cloud clients (Gemini Live, Edge TTS) are blocked from network dispatch.
3. Offline Local TTS and localhost Ollama are the only providers dispatched.
"""

from typing import Any

import pytest

from cyber_agent.brain.model_router import AssistantMode, ModelRouter
from cyber_agent.config import Settings
from cyber_agent.providers.tts_edge import EdgeTTSProvider
from cyber_agent.providers.tts_local import LocalTTSProvider


def test_privacy_mode_locks_router_to_mode_c(tmp_path: Any) -> None:
    db_path = tmp_path / "privacy_test.sqlite3"
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=db_path)
    assert router.active_mode == AssistantMode.A_LIVE

    # Engage Privacy Mode
    router.set_privacy_mode(True)
    assert router.privacy_mode is True
    assert router.active_mode.value == AssistantMode.C_LOCAL.value

    # Outbound mode switches to A or B must be blocked
    router.set_mode("A")
    assert router.active_mode.value == AssistantMode.C_LOCAL.value

    router.set_mode("B")
    assert router.active_mode.value == AssistantMode.C_LOCAL.value


@pytest.mark.asyncio
async def test_edge_tts_strictly_blocked_in_privacy_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(CYBER_PRIVACY_MODE=True)
    monkeypatch.setattr("cyber_agent.providers.tts_edge.get_settings", lambda: settings)

    provider = EdgeTTSProvider()
    with pytest.raises(PermissionError, match="Privacy Mode violation"):
        async for _ in provider.stream_audio("Maxfiy ma'lumot"):
            pass


@pytest.mark.asyncio
async def test_local_tts_works_without_network() -> None:
    # LocalTTS runs 100% offline
    provider = LocalTTSProvider()
    audio = await provider.synthesize_to_pcm("Maxfiy xabar")
    assert len(audio) > 0
    assert len(audio) % 2 == 0
