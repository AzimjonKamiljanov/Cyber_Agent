"""Intelligent Tri-Mode Router for Cyber Agent (Modes A, B, C).

Enforces MASTER_PLAN §5.3 rules:
- Mode A (Live): Audio-to-audio streaming via Gemini 3.8 Live (default, cloud allowed).
- Mode B (Cascade): Local Whisper STT -> Cloud LLM (Gemini text) -> Local/Edge TTS.
- Mode C (Local): Local Whisper STT -> Local Ollama -> Local TTS (offline, privacy).
- Privacy Mode: Forces Mode C strictly with ZERO outbound cloud packets.
- QuotaExhausted / Rate-limit: Zero retry loop, immediate fallback to Mode C.
- Internet Outage: Immediate fallback to Mode C.
- Mutating tool timeouts: Never auto-repeated.
- Persistent mode & privacy settings across sessions.
- Uzbek user notification on automatic mode switches.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Any

from cyber_agent.config import get_settings

logger = logging.getLogger(__name__)


class AssistantMode(str, Enum):
    A_LIVE = "A"
    B_CASCADE = "B"
    C_LOCAL = "C"


class ModelRouter:
    """Orchestrates routing between Live, Cascade, and Local operating modes."""

    def __init__(
        self,
        initial_mode: AssistantMode | str | None = None,
        privacy_mode: bool | None = None,
        db_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.data_dir = settings.cyber_data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (self.data_dir / "user_settings.sqlite3")

        self._init_db()

        # Load persisted settings or fallback to config
        persisted_privacy = self._load_setting("privacy_mode")
        if persisted_privacy is not None:
            self._privacy_mode = persisted_privacy.lower() in ("true", "1")
        else:
            self._privacy_mode = privacy_mode if privacy_mode is not None else settings.cyber_privacy_mode

        persisted_mode = self._load_setting("active_mode")
        if persisted_mode and persisted_mode in ("A", "B", "C"):
            target_mode = AssistantMode(persisted_mode)
        else:
            raw_mode = initial_mode or settings.cyber_mode
            target_mode = AssistantMode(raw_mode) if raw_mode in ("A", "B", "C") else AssistantMode.A_LIVE

        if self._privacy_mode:
            self._active_mode = AssistantMode.C_LOCAL
        else:
            self._active_mode = target_mode

        self._previous_mode = self._active_mode
        self._on_mode_change_callback: Any = None

    def _init_db(self) -> None:
        """Initialize settings SQLite table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def _load_setting(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _save_setting(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, time.time()),
            )
            conn.commit()

    @property
    def active_mode(self) -> AssistantMode:
        return self._active_mode

    @property
    def privacy_mode(self) -> bool:
        return self._privacy_mode

    def set_on_mode_change_callback(self, cb: Any) -> None:
        self._on_mode_change_callback = cb

    def _notify(self, message: str) -> None:
        logger.info("Router Event: %s (Active Mode: %s)", message, self._active_mode.value)
        if self._on_mode_change_callback:
            try:
                self._on_mode_change_callback(self._active_mode, message)
            except Exception as e:  # noqa: BLE001
                logger.error("Error in on_mode_change callback: %s", e)

    def set_privacy_mode(self, enabled: bool) -> str:
        """Toggle privacy mode. When enabled, strictly locks to Mode C."""
        self._privacy_mode = enabled
        self._save_setting("privacy_mode", str(enabled))

        if enabled:
            if self._active_mode != AssistantMode.C_LOCAL:
                self._previous_mode = self._active_mode
                self._active_mode = AssistantMode.C_LOCAL
                self._save_setting("active_mode", AssistantMode.C_LOCAL.value)
            msg = (
                "Maxfiylik rejimi (Privacy Mode) yoqildi. Barcha bulut aloqalari bloklandi, "
                "faqat to'liq mahalliy rejim (Mode C) ishlaydi."
            )
        else:
            # Restore previous non-private mode
            self._active_mode = self._previous_mode if self._previous_mode != AssistantMode.C_LOCAL else AssistantMode.A_LIVE
            self._save_setting("active_mode", self._active_mode.value)
            msg = f"Maxfiylik rejimi o'chirildi. Tizim {self._active_mode.value}-rejimga qaytarildi."

        self._notify(msg)
        return msg

    def set_mode(self, mode: AssistantMode | str) -> tuple[AssistantMode, str]:
        """Manually switch operating mode (A, B, or C)."""
        target = AssistantMode(mode) if isinstance(mode, str) else mode

        if self._privacy_mode and target != AssistantMode.C_LOCAL:
            msg = (
                "Maxfiylik rejimi yoqilganligi sababli bulut rejimlariga (A/B) o'tib bo'lmaydi. "
                "Oldin maxfiylik rejimini o'chiring."
            )
            return self._active_mode, msg

        self._previous_mode = self._active_mode
        self._active_mode = target
        self._save_setting("active_mode", target.value)

        names = {
            AssistantMode.A_LIVE: "Mode A (Gemini 3.8 Live ovozli oqim)",
            AssistantMode.B_CASCADE: "Mode B (Kaskad: mahalliy STT + bulut LLM + TTS)",
            AssistantMode.C_LOCAL: "Mode C (Mahalliy: to'liq offline Whisper + Ollama + TTS)",
        }
        msg = f"Tizim muvaffaqiyatli {names[target]}ga o'tkazildi."
        self._notify(msg)
        return self._active_mode, msg

    def handle_quota_exhausted(self) -> str:
        """Immediate fallback to Mode C on QuotaExhausted or RateLimit. Zero retry loop."""
        self._previous_mode = self._active_mode
        self._active_mode = AssistantMode.C_LOCAL
        self._save_setting("active_mode", AssistantMode.C_LOCAL.value)

        msg = (
            "Gemini kvotasi tugadi yoki cheklov yuz berdi. "
            "Tizim uzluksiz ishlash uchun avtomatik ravishda mahalliy Mode C rejimiga o'tdi."
        )
        self._notify(msg)
        return msg

    def handle_network_outage(self) -> str:
        """Immediate fallback to Mode C on network loss or DNS/socket failure."""
        self._previous_mode = self._active_mode
        self._active_mode = AssistantMode.C_LOCAL
        self._save_setting("active_mode", AssistantMode.C_LOCAL.value)

        msg = (
            "Internet aloqasi uzildi. "
            "Tizim avtomatik ravishda to'liq offline rejimga (Mode C) o'tdi."
        )
        self._notify(msg)
        return msg


_global_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    global _global_router
    if _global_router is None:
        _global_router = ModelRouter()
    return _global_router
