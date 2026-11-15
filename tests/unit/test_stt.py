"""Unit tests for local Whisper STT provider and Uzbek script transliteration."""

import numpy as np
import pytest

from cyber_agent.providers.stt_whisper import WhisperSTTProvider
from cyber_agent.providers.uzbek_script import cyrillic_to_latin


def test_cyrillic_to_latin() -> None:
    assert cyrillic_to_latin("") == ""
    assert cyrillic_to_latin("Салом") == "Salom"
    assert cyrillic_to_latin("Ўzbekiston") == "O'zbekiston"
    assert cyrillic_to_latin("Ғalaba") == "G'alaba"
    assert cyrillic_to_latin("Шahar") == "Shahar"
    assert cyrillic_to_latin("Чoy") == "Choy"
    assert cyrillic_to_latin("Яхши") == "Yaxshi"
    assert cyrillic_to_latin("Юлдуз") == "Yulduz"
    assert cyrillic_to_latin("Ер") == "Yer"
    assert cyrillic_to_latin("Бекат") == "Bekat"


def test_whisper_provider_init() -> None:
    provider = WhisperSTTProvider(model_id="tiny", device="cpu", compute_type="int8")
    assert not provider.is_loaded
    assert provider.model_id == "tiny"
    assert provider.preferred_device == "cpu"


def test_whisper_transcribe_empty_pcm() -> None:
    provider = WhisperSTTProvider(model_id="tiny", device="cpu", compute_type="int8")
    result = provider.transcribe_pcm(b"")
    assert result == ""


def test_whisper_transcribe_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = WhisperSTTProvider(model_id="tiny", device="cpu", compute_type="int8")

    class MockSegment:
        def __init__(self, text: str) -> None:
            self.text = text

    class MockWhisper:
        def transcribe(self, audio: np.ndarray, **kwargs: object) -> tuple[list[MockSegment], dict[str, str]]:
            return [MockSegment("Салом dunyo")], {"language": "uz"}

    provider._model = MockWhisper()
    # 1 second of silence (16000 int16 zeros = 32000 bytes)
    silence = np.zeros(16000, dtype=np.int16).tobytes()
    res = provider.transcribe_pcm(silence)
    assert res == "Salom dunyo"


def test_whisper_unload() -> None:
    provider = WhisperSTTProvider(model_id="tiny", device="cpu", compute_type="int8")
    provider._model = object()
    assert provider.is_loaded
    provider.unload()
    assert not provider.is_loaded
