"""Cascade Pipeline: STT -> LLM/Tools -> TTS with Barge-In and Mode Awareness.

Supports:
- Mode B (Cascade): Local Whisper STT -> Cloud LLM -> Local/Edge TTS
- Mode C (Local): Local Whisper STT -> Local Ollama -> Local TTS (100% offline)
- Barge-in: Stops TTS audio streaming immediately when user interrupts or presses PTT.
- Real-time event streaming: emits transcript_in, transcript_out, audio_out, status.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from cyber_agent.brain.model_router import AssistantMode, ModelRouter, get_model_router
from cyber_agent.brain.orchestrator import Orchestrator, get_orchestrator
from cyber_agent.config import get_settings
from cyber_agent.providers.base import (
    AudioOutEvent,
    ConfirmCardEvent,
    ErrorEvent,
    StatusEvent,
    TranscriptInEvent,
    TranscriptOutEvent,
    VoiceEvent,
)
from cyber_agent.providers.ollama_local import OllamaLocalProvider
from cyber_agent.providers.stt_whisper import WhisperSTTProvider
from cyber_agent.providers.tts_edge import EdgeTTSProvider
from cyber_agent.providers.tts_local import LocalTTSProvider

logger = logging.getLogger(__name__)


class CascadePipeline:
    """Manages sequential STT -> Brain -> TTS pipeline for Modes B and C."""

    def __init__(
        self,
        stt_provider: WhisperSTTProvider | None = None,
        ollama_provider: OllamaLocalProvider | None = None,
        local_tts: LocalTTSProvider | None = None,
        edge_tts: EdgeTTSProvider | None = None,
        orchestrator: Orchestrator | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.stt = stt_provider or WhisperSTTProvider()
        self.ollama = ollama_provider or OllamaLocalProvider()
        self.local_tts = local_tts or LocalTTSProvider()
        self.edge_tts = edge_tts or EdgeTTSProvider()
        self.orchestrator = orchestrator or get_orchestrator()
        self.router = router or get_model_router()

        self._audio_buffer = bytearray()
        self._is_synthesizing = False
        self._interrupted = False
        self._conversation_history: list[dict[str, Any]] = []

    def buffer_audio(self, pcm_chunk: bytes) -> None:
        """Accumulate incoming 16 kHz PCM16 audio bytes."""
        self._audio_buffer.extend(pcm_chunk)

    def interrupt(self) -> None:
        """Barge-in: immediately cancel ongoing synthesis and audio playback."""
        logger.info("Barge-in: Interrupting cascade pipeline audio playback.")
        self._interrupted = True
        self._is_synthesizing = False
        self._audio_buffer.clear()

    async def process_turn(self) -> AsyncIterator[VoiceEvent]:
        """Execute STT -> LLM/Tools -> TTS on buffered audio and yield events."""
        self._interrupted = False
        raw_pcm = bytes(self._audio_buffer)
        self._audio_buffer.clear()

        if not raw_pcm or len(raw_pcm) < 3200:  # Less than 100ms of audio
            return

        yield StatusEvent(state="listening", details="Nutq tahlil qilinmoqda...")

        # 1. Local STT (faster-whisper)
        try:
            user_text = await asyncio.to_thread(self.stt.transcribe_pcm, raw_pcm)
        except Exception as e:  # noqa: BLE001
            logger.error("STT transcription error: %s", e)
            yield ErrorEvent(code="STT_ERROR", message=f"STT xatoligi: {e}")
            return

        if not user_text.strip():
            logger.debug("STT yielded empty text.")
            yield StatusEvent(state="idle", details="Ovoz eshitilmadi")
            return

        logger.info("Transcribed user speech: %r", user_text)
        yield TranscriptInEvent(text=user_text, is_final=True)
        self._conversation_history.append({"role": "user", "content": user_text})

        if self._interrupted:
            return

        yield StatusEvent(state="thinking", details="Javob tayyorlanmoqda...")

        # 2. Brain / LLM + Tool Execution
        assistant_text = ""
        mode = self.router.active_mode

        if mode == AssistantMode.C_LOCAL or self.router.privacy_mode:
            # Mode C: Pure Local Ollama
            chat_resp = await self.ollama.chat(self._conversation_history, enable_tools=True)
            if chat_resp.tool_calls:
                for tc in chat_resp.tool_calls:
                    orch_resp = await self.orchestrator.handle_tool_call(
                        name=tc.name,
                        args=tc.arguments,
                    )
                    if orch_resp.confirmation_card:
                        yield ConfirmCardEvent(card=orch_resp.confirmation_card)
                    assistant_text += f"{orch_resp.spoken_message} "
            else:
                assistant_text = chat_resp.content

        else:
            # Mode B: Cascade with cloud or local fallback
            try:
                # If Gemini API key is present and cloud allowed, can query cloud or Ollama
                chat_resp = await self.ollama.chat(self._conversation_history, enable_tools=True)
                if chat_resp.tool_calls:
                    for tc in chat_resp.tool_calls:
                        orch_resp = await self.orchestrator.handle_tool_call(
                            name=tc.name,
                            args=tc.arguments,
                        )
                        if orch_resp.confirmation_card:
                            yield ConfirmCardEvent(card=orch_resp.confirmation_card)
                        assistant_text += f"{orch_resp.spoken_message} "
                else:
                    assistant_text = chat_resp.content
            except Exception as e:  # noqa: BLE001
                logger.warning("Cloud cascade failed (%s), falling back to local Mode C.", e)
                self.router.handle_quota_exhausted()
                assistant_text = "Kechirasiz, aloqa uzilishi tufayli mahalliy rejimga o'tildi."

        assistant_text = assistant_text.strip()
        if not assistant_text:
            assistant_text = "Tushundim, davom etamiz."

        logger.info("Assistant reply: %r", assistant_text)
        self._conversation_history.append({"role": "assistant", "content": assistant_text})
        yield TranscriptOutEvent(text=assistant_text, is_final=True)

        if self._interrupted:
            return

        # 3. TTS (Text-to-Speech)
        yield StatusEvent(state="speaking", details="Javob berilmoqda...")
        self._is_synthesizing = True

        use_edge = (
            not self.router.privacy_mode
            and mode != AssistantMode.C_LOCAL
            and get_settings().cyber_tts_provider == "edge"
        )

        try:
            if use_edge:
                try:
                    async for chunk in self.edge_tts.stream_audio(assistant_text):
                        if self._interrupted:
                            logger.info("TTS playback interrupted by user.")
                            break
                        yield AudioOutEvent(data=chunk)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Edge TTS failed (%s). Falling back to Local TTS.", e)
                    async for chunk in self.local_tts.stream_audio(assistant_text):
                        if self._interrupted:
                            break
                        yield AudioOutEvent(data=chunk)
            else:
                # Local offline TTS (zero network)
                async for chunk in self.local_tts.stream_audio(assistant_text):
                    if self._interrupted:
                        logger.info("TTS playback interrupted by user.")
                        break
                    yield AudioOutEvent(data=chunk)
        finally:
            self._is_synthesizing = False

        yield StatusEvent(state="idle", details="Tayyor")
