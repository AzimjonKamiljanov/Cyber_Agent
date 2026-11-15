"""Unit tests for Translation Mode (Stage S5)."""

import pytest

from cyber_agent.brain.translator import TranslationSession, handle_translate_mode
from cyber_agent.tools.schemas import TranslateModeArgs


def test_translation_session_activation_and_deactivation() -> None:
    """Test session lifecycle and mode toggles."""
    session = TranslationSession()
    assert session.is_active is False

    msg_act = session.activate(target_lang="en")
    assert session.is_active is True
    assert "Ingliz" in msg_act

    # Test phrase translation
    trans = session.translate_phrase("Salom dunyo")
    assert "[TARJIMA (EN)]" in trans

    # Test deactivation via phrase
    exit_msg = session.translate_phrase("Rejimdan chiq")
    assert session.is_active is False
    assert "o'chirildi" in exit_msg


@pytest.mark.asyncio
async def test_translate_mode_tool() -> None:
    """Test translate_mode tool handler."""
    session = TranslationSession()
    # Mock global session
    from cyber_agent.brain import translator

    translator._global_translation_session = session

    # Activation call
    res_act = await handle_translate_mode(TranslateModeArgs(target_language="ru"))
    assert res_act.success is True
    assert "Rus" in res_act.output
    assert session.is_active is True

    # Translation call
    res_tr = await handle_translate_mode(
        TranslateModeArgs(target_language="ru", text="Bugun ob-havo ajoyib")
    )
    assert res_tr.success is True
    assert "[TARJIMA (RU)]" in res_tr.output
