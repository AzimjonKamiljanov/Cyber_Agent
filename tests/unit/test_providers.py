"""Unit tests for Voice Providers (MockLive & GeminiLive interfaces)."""

import asyncio

import pytest

from cyber_agent.providers.base import (
    AudioOutEvent,
    QuotaExhaustedError,
    SessionClosedError,
    StatusEvent,
    TranscriptInEvent,
    TranscriptOutEvent,
)
from cyber_agent.providers.gemini_live import is_quota_error
from cyber_agent.providers.mock_live import MockLiveProvider


@pytest.mark.asyncio
async def test_mock_live_normal_flow() -> None:
    provider = MockLiveProvider(auto_reply=True)
    await provider.connect()

    events_received = []

    async def collect() -> None:
        async for event in provider.events():
            events_received.append(event)
            if isinstance(event, AudioOutEvent):
                break

    collect_task = asyncio.create_task(collect())

    # Send 16 kHz PCM16 mock audio chunk
    await provider.send_audio(b"\x00\x00" * 320)
    await asyncio.wait_for(collect_task, timeout=2.0)

    # Verify event types received
    types = [type(e) for e in events_received]
    assert StatusEvent in types
    assert TranscriptInEvent in types
    assert TranscriptOutEvent in types
    assert AudioOutEvent in types

    await provider.close()


@pytest.mark.asyncio
async def test_mock_live_interrupt_barge_in() -> None:
    provider = MockLiveProvider(auto_reply=True)
    await provider.connect()

    events_received = []

    async def collect() -> None:
        async for event in provider.events():
            events_received.append(event)
            if isinstance(event, StatusEvent) and event.state == "Interrupted":
                break

    collect_task = asyncio.create_task(collect())

    await provider.send_audio(b"\x00\x00" * 320)
    # Immediate barge-in
    await provider.interrupt()

    await asyncio.wait_for(collect_task, timeout=2.0)
    assert provider.interrupted is True

    await provider.close()


@pytest.mark.asyncio
async def test_mock_live_goaway_handling() -> None:
    provider = MockLiveProvider(simulate_goaway=True)
    await provider.connect()
    assert provider.reconnect_count == 1
    await provider.close()


@pytest.mark.asyncio
async def test_mock_live_quota_exhausted() -> None:
    provider = MockLiveProvider(simulate_quota_error=True)
    with pytest.raises(QuotaExhaustedError):
        await provider.connect()


@pytest.mark.asyncio
async def test_session_closed_error() -> None:
    provider = MockLiveProvider()
    await provider.close()
    with pytest.raises(SessionClosedError):
        await provider.send_audio(b"\x00\x00" * 160)


def test_is_quota_error_detection() -> None:
    assert is_quota_error(Exception("429 Too Many Requests")) is True
    assert is_quota_error(Exception("RESOURCE_EXHAUSTED: quota limit reached")) is True
    assert is_quota_error(Exception("Quota exceeded for project")) is True
    assert is_quota_error(Exception("Connection reset by peer")) is False
