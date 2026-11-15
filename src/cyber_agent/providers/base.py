"""Base abstractions and event models for Voice Providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


class VoiceProviderError(Exception):
    """Base error for voice providers."""

    def __init__(self, message: str, code: str = "PROVIDER_ERROR", retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable


class QuotaExhaustedError(VoiceProviderError):
    """Raised when cloud API quotas or rate limits are exhausted.

    Must never trigger automatic paid fallback.
    """

    def __init__(self, message: str = "API quota or rate limit exceeded") -> None:
        super().__init__(message=message, code="QUOTA_EXHAUSTED", retryable=False)


class SessionClosedError(VoiceProviderError):
    """Raised when the session is closed."""

    def __init__(self, message: str = "Session closed") -> None:
        super().__init__(message=message, code="SESSION_CLOSED", retryable=False)


@dataclass(frozen=True)
class AudioOutEvent:
    data: bytes
    sample_rate: int = 24000


@dataclass(frozen=True)
class TranscriptInEvent:
    text: str
    is_final: bool = False


@dataclass(frozen=True)
class TranscriptOutEvent:
    text: str
    is_final: bool = False


@dataclass(frozen=True)
class StatusEvent:
    state: str
    details: str = ""


@dataclass(frozen=True)
class ErrorEvent:
    code: str
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class ConfirmCardEvent:
    card: dict[str, Any]


VoiceEvent = AudioOutEvent | TranscriptInEvent | TranscriptOutEvent | StatusEvent | ErrorEvent | ConfirmCardEvent


class VoiceProvider(ABC):
    """Abstract interface for audio-to-audio and cascaded voice providers."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the voice provider."""

    @abstractmethod
    async def send_audio(self, pcm16_data: bytes) -> None:
        """Stream a chunk of PCM16 16 kHz mono audio into the session."""

    @abstractmethod
    async def interrupt(self) -> None:
        """Signal barge-in: flush local playback queues and interrupt generation."""

    @abstractmethod
    def events(self) -> AsyncIterator[VoiceEvent]:
        """Asynchronously iterate over incoming events from the provider."""

    @abstractmethod
    async def close(self) -> None:
        """Terminate provider connection and cleanup resources."""
