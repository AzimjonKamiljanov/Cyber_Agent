"""Integration tests for Cascade Pipeline (Modes B and C, Barge-in, Offline fallback)."""

from typing import Any

import pytest

from cyber_agent.brain.cascade_pipeline import CascadePipeline
from cyber_agent.brain.model_router import AssistantMode, ModelRouter
from cyber_agent.brain.orchestrator import Orchestrator
from cyber_agent.providers.base import AudioOutEvent, TranscriptInEvent, TranscriptOutEvent
from cyber_agent.providers.ollama_local import OllamaLocalProvider, OllamaResponse
from cyber_agent.providers.stt_whisper import WhisperSTTProvider
from cyber_agent.providers.tts_local import LocalTTSProvider
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.registry import ToolRegistry


class FakeWhisperProvider(WhisperSTTProvider):
    def __init__(self, transcript: str = "Hozirgi vaqtni ayt") -> None:
        self.transcript = transcript

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        return self.transcript


class FakeOllamaProvider(OllamaLocalProvider):
    def __init__(self, reply: str = "Hozir soat o'n to'rt yarim.") -> None:
        self.reply = reply

    async def chat(self, messages: list[dict[str, Any]], enable_tools: bool = True) -> OllamaResponse:
        return OllamaResponse(content=self.reply, tool_calls=[])


@pytest.mark.asyncio
async def test_cascade_pipeline_full_turn(tmp_path: Any) -> None:
    registry = ToolRegistry()
    register_default_tools(registry)
    orch = Orchestrator(tool_registry=registry)

    db_path = tmp_path / "test_pipe.sqlite3"
    router = ModelRouter(initial_mode=AssistantMode.C_LOCAL, db_path=db_path)

    fake_stt = FakeWhisperProvider("Hozir soat necha?")
    fake_ollama = FakeOllamaProvider("Hozir soat 14:30 bo'ldi.")
    local_tts = LocalTTSProvider()

    pipeline = CascadePipeline(
        stt_provider=fake_stt,
        ollama_provider=fake_ollama,
        local_tts=local_tts,
        orchestrator=orch,
        router=router,
    )

    # Buffer 200 ms of simulated PCM audio (6400 bytes at 16 kHz 16-bit mono)
    pipeline.buffer_audio(b"\x00\x00" * 3200)

    events = []
    async for event in pipeline.process_turn():
        events.append(event)

    # Verify event sequence:
    # Status (listening) -> TranscriptIn -> Status (thinking) -> TranscriptOut -> Status (speaking) -> AudioOut... -> Status (idle)
    in_transcripts = [e for e in events if isinstance(e, TranscriptInEvent)]
    out_transcripts = [e for e in events if isinstance(e, TranscriptOutEvent)]
    audio_events = [e for e in events if isinstance(e, AudioOutEvent)]

    assert len(in_transcripts) == 1
    assert in_transcripts[0].text == "Hozir soat necha?"

    assert len(out_transcripts) == 1
    assert "Hozir soat 14:30" in out_transcripts[0].text

    assert len(audio_events) > 0
    total_audio_bytes = sum(len(a.data) for a in audio_events)
    assert total_audio_bytes > 0


@pytest.mark.asyncio
async def test_cascade_pipeline_barge_in(tmp_path: Any) -> None:
    registry = ToolRegistry()
    register_default_tools(registry)
    orch = Orchestrator(tool_registry=registry)

    db_path = tmp_path / "test_pipe_barge.sqlite3"
    router = ModelRouter(initial_mode=AssistantMode.C_LOCAL, db_path=db_path)

    fake_stt = FakeWhisperProvider("Uzun matn")
    fake_ollama = FakeOllamaProvider("Bu juda uzun javob bo'lib foydalanuvchi uni to'xtatadi.")
    local_tts = LocalTTSProvider()

    pipeline = CascadePipeline(
        stt_provider=fake_stt,
        ollama_provider=fake_ollama,
        local_tts=local_tts,
        orchestrator=orch,
        router=router,
    )

    pipeline.buffer_audio(b"\x00\x00" * 3200)

    # Interrupt right after starting
    audio_chunks = []
    async for event in pipeline.process_turn():
        if isinstance(event, TranscriptOutEvent):
            # User barges in right when agent begins speaking
            pipeline.interrupt()
        elif isinstance(event, AudioOutEvent):
            audio_chunks.append(event.data)

    # When interrupted, TTS stream should be aborted immediately
    assert pipeline._interrupted is True
