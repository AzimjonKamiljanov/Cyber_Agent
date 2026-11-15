#!/usr/bin/env python3
"""
Terminal Proof-of-Concept for Cyber Agent voice conversation.
Uses sounddevice for microphone input and speaker playback.
Supports a 5-minute conversation surviving GoAway reconnects.
"""

import argparse
import asyncio
import threading

import sounddevice as sd

from cyber_agent.config import get_settings
from cyber_agent.providers.base import (
    AudioOutEvent,
    ErrorEvent,
    StatusEvent,
    TranscriptInEvent,
    TranscriptOutEvent,
    VoiceProvider,
)
from cyber_agent.providers.gemini_live import GeminiLiveProvider
from cyber_agent.providers.mock_live import MockLiveProvider

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHUNK_DURATION = 0.04  # 40 ms
INPUT_CHUNK_SIZE = int(INPUT_SAMPLE_RATE * CHUNK_DURATION)


class TerminalVoiceApp:
    def __init__(self, provider: VoiceProvider) -> None:
        self.provider = provider
        self.is_talking = False
        self.is_running = True
        self.audio_out_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.loop: asyncio.AbstractEventLoop | None = None

    def _audio_input_callback(self, indata: bytes, frames: int, time_info: object, status: object) -> None:
        if self.is_talking and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.provider.send_audio(bytes(indata)),
                self.loop,
            )

    async def _audio_playback_worker(self) -> None:
        """Play incoming 24 kHz audio chunks via sounddevice RawOutputStream."""
        try:
            with sd.RawOutputStream(
                samplerate=OUTPUT_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=1024,
            ) as stream:
                while self.is_running:
                    chunk = await self.audio_out_queue.get()
                    stream.write(chunk)
                    self.audio_out_queue.task_done()
        except sd.PortAudioError as e:
            print(f"\n[Audio Playback Warning]: {e}")

    async def _event_listener(self) -> None:
        """Process stream events from VoiceProvider."""
        try:
            async for event in self.provider.events():
                if isinstance(event, TranscriptInEvent):
                    status_flag = "[Yakuniy]" if event.is_final else "[...]"
                    print(f"\n[Siz ({status_flag})]: {event.text}")
                elif isinstance(event, TranscriptOutEvent):
                    status_flag = "[Yakuniy]" if event.is_final else "[...]"
                    print(f"\n[Cyber Agent ({status_flag})]: {event.text}")
                elif isinstance(event, AudioOutEvent):
                    await self.audio_out_queue.put(event.data)
                elif isinstance(event, StatusEvent):
                    print(f"\n[Holat]: {event.state} {event.details}")
                elif isinstance(event, ErrorEvent):
                    print(f"\n[Xatolik]: {event.code} — {event.message}")
        except asyncio.CancelledError:
            pass

    def _user_input_thread(self) -> None:
        """Handle keyboard input in a separate thread."""
        while self.is_running:
            try:
                line = input()
                if line.strip().lower() == "q":
                    self.is_running = False
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.provider.close(), self.loop)
                    break

                self.is_talking = not self.is_talking
                if self.is_talking:
                    print("\n>>> [MIKROFON YOQILDI] Gapiring... (To'xtatish uchun yana Enter bosing)")
                else:
                    print("\n--- [MIKROFON O'CHIRILDI] Javob kutilmoqda... (Boshlash uchun Enter bosing)")
            except (EOFError, KeyboardInterrupt):
                self.is_running = False
                break

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        print("=== Cyber Agent Terminal Voice PoC ===")
        print("Ulanmoqda...")

        await self.provider.connect()
        print("\nUlandi! Boshqaruv:")
        print("  - [Enter] bosish: Gapirishni boshlash / to'xtatish (PTT)")
        print("  - 'q' yozib [Enter] bosish: Chiqish")

        listener_task = asyncio.create_task(self._event_listener())
        playback_task = asyncio.create_task(self._audio_playback_worker())

        # Start input thread
        thread = threading.Thread(target=self._user_input_thread, daemon=True)
        thread.start()

        try:
            with sd.RawInputStream(
                samplerate=INPUT_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=INPUT_CHUNK_SIZE,
                callback=self._audio_input_callback,
            ):
                while self.is_running:
                    await asyncio.sleep(0.1)
        except sd.PortAudioError as e:
            print(f"\n[Audio Input Xatosi]: {e}")
        finally:
            self.is_running = False
            listener_task.cancel()
            playback_task.cancel()
            await self.provider.close()
            print("\nSessiya yakunlandi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber Agent Terminal Live Voice Test")
    parser.add_argument("--mock", action="store_true", help="Use MockLiveProvider instead of Gemini Live API")
    args = parser.parse_args()

    settings = get_settings()
    if args.mock or not settings.gemini_api_key:
        if not args.mock:
            print("OGOHLANTIRISH: GEMINI_API_KEY topilmadi. MockLiveProvider ishlatilmoqda.")
        provider: VoiceProvider = MockLiveProvider()
    else:
        provider = GeminiLiveProvider(settings)

    try:
        asyncio.run(TerminalVoiceApp(provider).run())
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")


if __name__ == "__main__":
    main()
