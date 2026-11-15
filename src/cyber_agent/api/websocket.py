"""WebSocket audio streaming gateway for Cyber Agent.

Handles binary PCM16 audio, JSON control messages (PTT, barge-in, STOP),
pairing-token authentication, origin verification, and single-session enforcement.
"""

import asyncio
import json
import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from cyber_agent.config import Settings, get_settings
from cyber_agent.providers.base import (
    AudioOutEvent,
    ErrorEvent,
    QuotaExhaustedError,
    SessionClosedError,
    StatusEvent,
    TranscriptInEvent,
    TranscriptOutEvent,
    VoiceProvider,
)
from cyber_agent.providers.gemini_live import GeminiLiveProvider
from cyber_agent.providers.mock_live import MockLiveProvider

logger = logging.getLogger(__name__)
ws_router = APIRouter()

MAX_BINARY_FRAME_SIZE = 65536  # 64 KB limit for binary audio frames
MAX_JSON_MESSAGE_SIZE = 4096   # 4 KB limit for JSON control messages

# Session lock and active websocket tracker to enforce single active session
_active_session_lock = asyncio.Lock()
_current_websocket: WebSocket | None = None


def is_allowed_origin(origin: str | None) -> bool:
    """Validate Origin header against permitted localhost and tailscale hosts."""
    if origin is None:
        return True  # Non-browser clients (scripts, tests)
    origin_lower = origin.lower()
    return (
        "127.0.0.1" in origin_lower
        or "localhost" in origin_lower
        or origin_lower.endswith(".ts.net")
        or ".ts.net:" in origin_lower
    )


def create_provider(settings: Settings) -> VoiceProvider:
    if settings.gemini_api_key:
        return GeminiLiveProvider(settings)
    return MockLiveProvider()


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    global _current_websocket
    settings = get_settings()

    # 1. Validate Origin header
    origin = websocket.headers.get("origin")
    if not is_allowed_origin(origin):
        logger.warning("Rejected WebSocket connection from unauthorized origin: %s", origin)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return

    # 2. Validate Pairing Token from Query Params
    query_params = parse_qs(websocket.scope.get("query_string", b"").decode("utf-8"))
    token_list = query_params.get("token", [])
    provided_token = token_list[0] if token_list else ""

    # If CYBER_PAIRING_TOKEN is set in settings, enforce exact match
    expected_token = settings.cyber_pairing_token
    if expected_token and provided_token != expected_token:
        logger.warning("Rejected WebSocket connection due to invalid pairing token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid pairing token")
        return

    await websocket.accept()

    # 3. Enforce Single Active Session
    async with _active_session_lock:
        if _current_websocket is not None and _current_websocket != websocket:
            try:
                await _current_websocket.close(
                    code=status.WS_1000_NORMAL_CLOSURE,
                    reason="New session connected",
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("Error closing existing websocket session: %s", e)
        _current_websocket = websocket

    provider: VoiceProvider = getattr(websocket.app.state, "voice_provider", None) or create_provider(settings)
    is_stopped = False

    try:
        await provider.connect()
    except QuotaExhaustedError:
        await websocket.send_text(
            json.dumps({"type": "error", "code": "QUOTA_EXHAUSTED", "message": "API quota exceeded"})
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to connect provider for websocket: %s", e)
        await websocket.send_text(
            json.dumps({"type": "error", "code": "CONNECTION_FAILED", "message": "Connection to provider failed"})
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    async def forward_provider_events() -> None:
        try:
            async for event in provider.events():
                if is_stopped:
                    continue

                if isinstance(event, AudioOutEvent):
                    await websocket.send_bytes(event.data)
                elif isinstance(event, TranscriptInEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "transcript_in",
                            "text": event.text,
                            "is_final": event.is_final,
                        })
                    )
                elif isinstance(event, TranscriptOutEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "transcript_out",
                            "text": event.text,
                            "is_final": event.is_final,
                        })
                    )
                elif isinstance(event, StatusEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "status",
                            "state": event.state,
                            "details": event.details,
                        })
                    )
                elif isinstance(event, ErrorEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "code": event.code,
                            "message": event.message,
                        })
                    )
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as err:  # noqa: BLE001
            logger.debug("Error in forward_provider_events: %s", err)

    event_task = asyncio.create_task(forward_provider_events())

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            # Handle Binary Audio Frames (16 kHz PCM16 mono)
            if "bytes" in message and message["bytes"] is not None:
                audio_bytes = message["bytes"]
                if len(audio_bytes) > MAX_BINARY_FRAME_SIZE:
                    await websocket.send_text(
                        json.dumps({"type": "error", "code": "FRAME_TOO_LARGE", "message": "Audio chunk exceeded size limit"})
                    )
                    continue

                if not is_stopped:
                    try:
                        await provider.send_audio(audio_bytes)
                    except QuotaExhaustedError:
                        await websocket.send_text(
                            json.dumps({"type": "error", "code": "QUOTA_EXHAUSTED", "message": "API quota exceeded"})
                        )
                    except SessionClosedError:
                        break

            # Handle JSON Control Messages
            elif "text" in message and message["text"] is not None:
                text_data = message["text"]
                if len(text_data) > MAX_JSON_MESSAGE_SIZE:
                    continue

                try:
                    payload = json.loads(text_data)
                except json.JSONDecodeError:
                    continue

                ctrl_type = payload.get("type")

                if ctrl_type == "ptt_start":
                    # User pressed Push-to-Talk: trigger barge-in / interrupt model output
                    await provider.interrupt()
                    await websocket.send_text(json.dumps({"type": "status", "state": "Listening"}))

                elif ctrl_type == "ptt_end":
                    await websocket.send_text(json.dumps({"type": "status", "state": "Thinking"}))

                elif ctrl_type == "stop":
                    # In-process emergency STOP
                    is_stopped = True
                    await provider.interrupt()
                    await websocket.send_text(json.dumps({"type": "status", "state": "Stopped"}))

                elif ctrl_type == "resume":
                    is_stopped = False
                    await websocket.send_text(json.dumps({"type": "status", "state": "Idle"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        logger.debug("Websocket connection exception: %s", e)
    finally:
        event_task.cancel()
        try:
            await event_task
        except asyncio.CancelledError:
            pass

        await provider.close()

        async with _active_session_lock:
            if _current_websocket == websocket:
                _current_websocket = None
