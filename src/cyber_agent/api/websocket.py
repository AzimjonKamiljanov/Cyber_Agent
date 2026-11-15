"""WebSocket audio streaming gateway for Cyber Agent.

Handles binary PCM16 audio, JSON control messages (PTT, barge-in, STOP),
pairing-token authentication, origin verification, and single-session enforcement.
Integrates ModelRouter (Mode A Live, Mode B Cascade, Mode C Local) and Privacy Mode.
"""

from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from cyber_agent.brain.cascade_pipeline import CascadePipeline
from cyber_agent.brain.model_router import AssistantMode, ModelRouter, get_model_router
from cyber_agent.brain.orchestrator import get_orchestrator
from cyber_agent.config import Settings, get_settings
from cyber_agent.providers.base import (
    AudioOutEvent,
    ConfirmCardEvent,
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
    if settings.gemini_api_key and not settings.cyber_privacy_mode:
        return GeminiLiveProvider(settings)
    return MockLiveProvider()


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    global _current_websocket
    settings = get_settings()
    router: ModelRouter = getattr(websocket.app.state, "model_router", None) or get_model_router()

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
            except Exception as e:  # noqa: BLE001  # noqa: BLE001
                logger.debug("Error closing existing websocket session: %s", e)
        _current_websocket = websocket

    # Send initial mode status to client
    await websocket.send_text(
        json.dumps({
            "type": "mode_status",
            "mode": router.active_mode.value,
            "privacy_mode": router.privacy_mode,
        })
    )

    provider: VoiceProvider = getattr(websocket.app.state, "voice_provider", None) or create_provider(settings)
    cascade = CascadePipeline(router=router)
    is_stopped = False
    turn_task: asyncio.Task[None] | None = None

    # Connect Mode A provider if active and cloud allowed
    if router.active_mode == AssistantMode.A_LIVE and not router.privacy_mode:
        try:
            await provider.connect()
        except QuotaExhaustedError:
            router.handle_quota_exhausted()
            await websocket.send_text(
                json.dumps({
                    "type": "mode_status",
                    "mode": router.active_mode.value,
                    "privacy_mode": router.privacy_mode,
                })
            )
        except Exception as e:  # noqa: BLE001  # noqa: BLE001
            logger.warning("Live provider connect failed (%s), switching to local Mode C.", e)
            router.handle_network_outage()
            await websocket.send_text(
                json.dumps({
                    "type": "mode_status",
                    "mode": router.active_mode.value,
                    "privacy_mode": router.privacy_mode,
                })
            )

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
                elif isinstance(event, ConfirmCardEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "confirm_card",
                            "card": event.card,
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

    async def run_cascade_turn() -> None:
        try:
            async for event in cascade.process_turn():
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
                elif isinstance(event, ConfirmCardEvent):
                    await websocket.send_text(
                        json.dumps({
                            "type": "confirm_card",
                            "card": event.card,
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
        except Exception as e:  # noqa: BLE001
            logger.error("Error in cascade turn: %s", e)

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            # Binary Audio Frames (16 kHz PCM16 mono)
            if "bytes" in message and message["bytes"] is not None:
                audio_bytes = message["bytes"]
                if len(audio_bytes) > MAX_BINARY_FRAME_SIZE:
                    await websocket.send_text(
                        json.dumps({"type": "error", "code": "FRAME_TOO_LARGE", "message": "Audio chunk exceeded size limit"})
                    )
                    continue

                if not is_stopped:
                    if router.active_mode == AssistantMode.A_LIVE and not router.privacy_mode:
                        try:
                            await provider.send_audio(audio_bytes)
                        except QuotaExhaustedError:
                            router.handle_quota_exhausted()
                            await websocket.send_text(
                                json.dumps({
                                    "type": "mode_status",
                                    "mode": router.active_mode.value,
                                    "privacy_mode": router.privacy_mode,
                                })
                            )
                        except SessionClosedError:
                            break
                    else:
                        # Cascade / Local Mode buffer
                        cascade.buffer_audio(audio_bytes)

            # JSON Control Messages
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
                    # Push-to-Talk pressed: Barge-in
                    if router.active_mode == AssistantMode.A_LIVE and not router.privacy_mode:
                        await provider.interrupt()
                    else:
                        cascade.interrupt()
                    await websocket.send_text(json.dumps({"type": "status", "state": "Listening"}))

                elif ctrl_type == "ptt_end":
                    if router.active_mode == AssistantMode.A_LIVE and not router.privacy_mode:
                        await websocket.send_text(json.dumps({"type": "status", "state": "Thinking"}))
                    else:
                        # Process cascade turn
                        if turn_task and not turn_task.done():
                            turn_task.cancel()
                        turn_task = asyncio.create_task(run_cascade_turn())

                elif ctrl_type == "stop":
                    # Emergency STOP
                    is_stopped = True
                    if router.active_mode == AssistantMode.A_LIVE and not router.privacy_mode:
                        await provider.interrupt()
                    else:
                        cascade.interrupt()
                    await websocket.send_text(json.dumps({"type": "status", "state": "Stopped"}))

                elif ctrl_type == "resume":
                    is_stopped = False
                    await websocket.send_text(json.dumps({"type": "status", "state": "Idle"}))

                elif ctrl_type == "get_mode":
                    await websocket.send_text(
                        json.dumps({
                            "type": "mode_status",
                            "mode": router.active_mode.value,
                            "privacy_mode": router.privacy_mode,
                        })
                    )

                elif ctrl_type == "set_mode":
                    target_mode = payload.get("mode")
                    new_mode, msg = router.set_mode(target_mode)
                    await websocket.send_text(
                        json.dumps({
                            "type": "mode_status",
                            "mode": new_mode.value,
                            "privacy_mode": router.privacy_mode,
                        })
                    )
                    await websocket.send_text(
                        json.dumps({"type": "status", "state": "Idle", "details": msg})
                    )

                elif ctrl_type == "set_privacy_mode":
                    enabled = bool(payload.get("enabled", False))
                    msg = router.set_privacy_mode(enabled)
                    await websocket.send_text(
                        json.dumps({
                            "type": "mode_status",
                            "mode": router.active_mode.value,
                            "privacy_mode": router.privacy_mode,
                        })
                    )
                    await websocket.send_text(
                        json.dumps({"type": "status", "state": "Idle", "details": msg})
                    )

                elif ctrl_type == "confirm_response":
                    action_id = str(payload.get("action_id", ""))
                    token = str(payload.get("token", ""))
                    approved = bool(payload.get("approved", False))
                    orchestrator = get_orchestrator()

                    if not approved:
                        orchestrator.confirmation_store.invalidate_confirmation(action_id)
                        await websocket.send_text(
                            json.dumps({
                                "type": "status",
                                "state": "Idle",
                                "details": "Amal bekor qilindi.",
                            })
                        )
                    else:
                        conf = orchestrator.confirmation_store.get_confirmation(action_id)
                        if conf:
                            resp = await orchestrator.handle_tool_call(
                                name=conf["tool_name"],
                                args=conf["args"],
                                action_id=action_id,
                                confirmation_token=token,
                            )
                            await websocket.send_text(
                                json.dumps({
                                    "type": "transcript_out",
                                    "text": resp.spoken_message,
                                    "is_final": True,
                                })
                            )
                        else:
                            await websocket.send_text(
                                json.dumps({
                                    "type": "error",
                                    "code": "CONFIRM_NOT_FOUND",
                                    "message": "Tasdiqlash so'rovi topilmadi yoki muddati o'tgan.",
                                })
                            )

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        logger.debug("Websocket connection exception: %s", e)
    finally:
        event_task.cancel()
        if turn_task and not turn_task.done():
            turn_task.cancel()
        try:
            await event_task
        except asyncio.CancelledError:
            pass

        await provider.close()

        async with _active_session_lock:
            if _current_websocket == websocket:
                _current_websocket = None
