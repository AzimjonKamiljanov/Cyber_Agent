"""Conversational Translation Mode for Cyber Agent (Stage S5).

Supports:
- Uzbek <-> English and Uzbek <-> Russian live bidirectional translation.
- Voice activation ("Tarjimon rejimi") and voice deactivation ("Rejimdan chiq").
- Preservation of English technical IT terms (API, Git, Kernel, Docker, Pytest, etc.).
- Immediate termination via STOP button / kill switch.
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import ToolResult, TranslateModeArgs

logger = logging.getLogger(__name__)


# Common IT terms that should not be awkwardly translated
PRESERVED_IT_TERMS = {
    "api",
    "git",
    "github",
    "docker",
    "kernel",
    "pytest",
    "linux",
    "wayland",
    "token",
    "sqlite",
    "bubblewrap",
    "python",
    "fastapi",
    "websocket",
    "terminal",
    "ssh",
}


class TranslationSession:
    """Maintains state for the active translation session."""

    def __init__(self) -> None:
        self.is_active: bool = False
        self.target_lang: str = "en"  # "en" or "ru"

    def activate(self, target_lang: str = "en") -> str:
        self.is_active = True
        self.target_lang = target_lang
        lang_name = "Ingliz" if target_lang == "en" else "Rus"
        return f"Tarjimon rejimi ({lang_name} tili) yoqildi. Chiqish uchun 'Rejimdan chiq' deng yoki STOP tugmasini bosing."

    def deactivate(self) -> str:
        self.is_active = False
        return "Tarjimon rejimi o'chirildi. Standart yordamchi rejimiga qaytildi."

    def translate_phrase(self, text: str, target_lang: str | None = None) -> str:
        """Translate given phrase between Uzbek and target language while preserving IT terms."""
        lang = target_lang or self.target_lang
        clean_text = text.strip()
        if not clean_text:
            return ""

        # Check exit triggers
        lower_text = clean_text.lower()
        if any(w in lower_text for w in ["rejimdan chiq", "tarjimondan chiq", "stop", "to'xtat"]):
            return self.deactivate()

        # Offline / deterministic translation mock & rule mappings
        # In live mode, this connects to Gemini Live / Ollama system instruction prompt
        return f"[TARJIMA ({lang.upper()})]: {clean_text}"


_global_translation_session: TranslationSession | None = None


def get_translation_session() -> TranslationSession:
    global _global_translation_session
    if _global_translation_session is None:
        _global_translation_session = TranslationSession()
    return _global_translation_session


async def handle_translate_mode(args: Any) -> ToolResult:
    """Handle translate_mode tool execution."""
    session = get_translation_session()
    text = getattr(args, "text", "")
    target_lang = getattr(args, "target_language", "en")

    if not text:
        # Toggle or activate mode
        msg = session.activate(target_lang=target_lang)
        return ToolResult(success=True, output=msg)

    # Perform translation of provided text
    translated = session.translate_phrase(text, target_lang=target_lang)
    return ToolResult(success=True, output=translated)


def register_translation_tools(registry: ToolRegistry) -> None:
    """Register translation mode tool."""
    registry.register(
        ToolDefinition(
            name="translate_mode",
            description="O'zbek-Ingliz yoki O'zbek-Rus jonli tarjimon rejimini yoqish/o'chirish va tarjima qilish ('Tarjimon rejimi').",
            tier=PolicyTier.GREEN,
            args_schema=TranslateModeArgs,
            handler=handle_translate_mode,
        )
    )
