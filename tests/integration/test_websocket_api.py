"""Integration tests for WebSocket Gateway and HTTP API."""

import json
from unittest import mock

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cyber_agent.config import Settings
from cyber_agent.main import app
from cyber_agent.providers.mock_live import MockLiveProvider


@pytest.fixture(autouse=True)
def _setup_app_provider() -> None:
    # Use fresh MockLiveProvider for tests
    app.state.voice_provider = MockLiveProvider()


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "stage": "s1", "mode": "live"}


def test_socket_binding() -> None:
    settings = Settings()
    # Invariant: Must bind 127.0.0.1 strictly, never 0.0.0.0
    assert settings.cyber_host == "127.0.0.1"
    assert settings.cyber_host != "0.0.0.0"


def test_bad_token_rejected() -> None:
    test_settings = Settings(CYBER_PAIRING_TOKEN="secret-pairing-1234")
    with (
        mock.patch("cyber_agent.api.websocket.get_settings", return_value=test_settings),
        pytest.raises(WebSocketDisconnect) as exc_info,
    ):
        client = TestClient(app)
        with client.websocket_connect("/ws/voice?token=wrong-token"):
            pass
    assert exc_info.value.code == 1008


def test_wrong_origin_rejected() -> None:
    client = TestClient(app)
    headers = {"origin": "https://malicious.attacker.com"}
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect("/ws/voice?token=", headers=headers),
    ):
        pass
    assert exc_info.value.code == 1008


def test_audio_streaming_and_transcripts() -> None:
    app.state.voice_provider = MockLiveProvider(auto_reply=True)
    client = TestClient(app)

    with client.websocket_connect("/ws/voice?token=") as ws:
        # Receive initial Connected status event
        initial_msg = json.loads(ws.receive_text())
        assert initial_msg["type"] == "status"
        assert initial_msg["state"] == "Connected"

        # Send binary audio chunk (16 kHz PCM16 mono)
        ws.send_bytes(b"\x00\x00" * 320)

        # Receive transcript_in
        t_in = json.loads(ws.receive_text())
        assert t_in["type"] == "transcript_in"
        assert "Salom" in t_in["text"]

        # Receive transcript_out
        t_out = json.loads(ws.receive_text())
        assert t_out["type"] == "transcript_out"
        assert "Assalomu alaykum" in t_out["text"]

        # Receive binary audio chunk
        audio_chunk = ws.receive_bytes()
        assert len(audio_chunk) > 0


def test_barge_in_and_stop() -> None:
    app.state.voice_provider = MockLiveProvider(auto_reply=True)
    client = TestClient(app)

    with client.websocket_connect("/ws/voice?token=") as ws:
        # Consume initial Connected status
        _ = ws.receive_text()

        # Send ptt_start (triggers barge-in / interrupt)
        ws.send_text(json.dumps({"type": "ptt_start"}))

        # Receive StatusEvents (Listening from gateway and/or Interrupted from provider)
        msg1 = json.loads(ws.receive_text())
        assert msg1["type"] == "status"
        assert msg1["state"] in {"Listening", "Interrupted"}

        msg2 = json.loads(ws.receive_text())
        assert msg2["type"] == "status"
        assert msg2["state"] in {"Listening", "Interrupted"}

        # Trigger emergency STOP
        ws.send_text(json.dumps({"type": "stop"}))
        status3 = json.loads(ws.receive_text())
        assert status3["type"] == "status"
        if status3["state"] == "Interrupted":
            status3 = json.loads(ws.receive_text())
        assert status3["state"] == "Stopped"

        # Resume from STOP
        ws.send_text(json.dumps({"type": "resume"}))
        status4 = json.loads(ws.receive_text())
        assert status4["type"] == "status"
        assert status4["state"] == "Idle"
