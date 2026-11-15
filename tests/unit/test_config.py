"""Unit tests for configuration and secret masking."""

import os
from unittest import mock

from cyber_agent.config import Settings


def test_settings_secret_masking() -> None:
    settings = Settings(
        GEMINI_API_KEY="secret-api-key-12345",
        CYBER_PAIRING_TOKEN="token-abc-9876",
        CYBER_LIVE_MODEL="gemini-3.8-live",
    )

    repr_str = repr(settings)
    assert "secret-api-key-12345" not in repr_str
    assert "token-abc-9876" not in repr_str
    assert "***" in repr_str

    str_str = str(settings)
    assert "secret-api-key-12345" not in str_str
    assert "token-abc-9876" not in str_str

    safe = settings.safe_dict()
    assert safe["gemini_api_key"] == "***"
    assert safe["cyber_pairing_token"] == "***"
    assert safe["cyber_live_model"] == "gemini-3.8-live"


def test_settings_default_values() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.cyber_host == "127.0.0.1"
        assert settings.cyber_port == 8000
        assert settings.cyber_live_model == "gemini-3.8-live"
        assert settings.cyber_address_as == "Azimjon"
        assert settings.cyber_privacy_mode is False
