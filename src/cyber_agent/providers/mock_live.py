"""Mock Live Voice Provider for deterministic testing."""

import asyncio
from collections.abc import AsyncIterator

from cyber_agent.providers.base import (
    AudioOutEvent,
    QuotaExhaustedError,
    SessionClosedError,
    StatusEvent,
    TranscriptInEvent,
    TranscriptOutEvent,
    VoiceEvent,
    VoiceProvider,
)


class MockLiveProvider(VoiceProvider):
    """Deterministic mock provider simulating Gemini 3.8 Live."""

    def __init__(
        self,
        auto_reply: bool = True,
        simulate_quota_error: bool = False,
        simulate_goaway: bool = False,
    ) -> None:
        self.auto_reply = auto_reply
        self.simulate_quota_error = simulate_quota_error
        self.simulate_goaway = simulate_goaway

        self.is_connected = False
        self.is_closed = False
        self.reconnect_count = 0
        self.interrupted = False
        self._event_queue: asyncio.Queue[VoiceEvent] = asyncio.Queue()
        self._active_reply_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        if self.is_closed:
            raise SessionClosedError("Cannot connect closed mock provider")
        if self.simulate_quota_error:
            raise QuotaExhaustedError("Simulated quota exhaustion (429)")

        self.is_connected = True
        await self._event_queue.put(StatusEvent(state="Connected", details="MockLiveProvider"))

        if self.simulate_goaway:
            self.simulate_goaway = False
            await self._event_queue.put(StatusEvent(state="GoAway", details="time_left: 5s"))
            self.reconnect_count += 1
            await self._event_queue.put(StatusEvent(state="Connected", details="Reconnected"))

    async def send_audio(self, pcm16_data: bytes) -> None:
        if not self.is_connected or self.is_closed:
            raise SessionClosedError("Session is closed or not connected")

        if self.simulate_quota_error:
            raise QuotaExhaustedError("Simulated quota error during stream")

        if self.auto_reply:
            if self._active_reply_task and not self._active_reply_task.done():
                self._active_reply_task.cancel()
            self._active_reply_task = asyncio.create_task(self._generate_reply())

    async def _generate_reply(self) -> None:
        try:
            # 1. User transcript
            await asyncio.sleep(0.01)
            await self._event_queue.put(
                TranscriptInEvent(text="Salom Cyber Agent", is_final=True)
            )

            # 2. Agent transcript
            await asyncio.sleep(0.01)
            await self._event_queue.put(
                TranscriptOutEvent(text="Assalomu alaykum, Azimjon!", is_final=True)
            )

            # 3. Agent audio frames (mock PCM16 24 kHz)
            mock_audio = b"\x00\x00" * 480  # 20ms of silence at 24kHz
            for _ in range(5):
                await asyncio.sleep(0.02)
                await self._event_queue.put(AudioOutEvent(data=mock_audio, sample_rate=24000))

        except asyncio.CancelledError:
            pass

    async def interrupt(self) -> None:
        self.interrupted = True
        if self._active_reply_task and not self._active_reply_task.done():
            self._active_reply_task.cancel()
            self._active_reply_task = None
        await self._event_queue.put(StatusEvent(state="Interrupted"))

    async def events(self) -> AsyncIterator[VoiceEvent]:
        while not self.is_closed:
            event = await self._event_queue.get()
            yield event
            self._event_queue.task_done()

    async def close(self) -> None:
        self.is_closed = True
        self.is_connected = False
        if self._active_reply_task and not self._active_reply_task.done():
            self._active_reply_task.cancel()
        await self._event_queue.put(StatusEvent(state="Closed"))
