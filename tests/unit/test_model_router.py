"""Unit tests for ModelRouter (Mode A/B/C routing, Privacy Mode, and fallbacks)."""

from pathlib import Path

import pytest

from cyber_agent.brain.model_router import AssistantMode, ModelRouter


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_settings.sqlite3"


def test_model_router_defaults(temp_db: Path) -> None:
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    assert router.active_mode == AssistantMode.A_LIVE
    assert not router.privacy_mode


def test_model_router_manual_switch(temp_db: Path) -> None:
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    mode, msg = router.set_mode(AssistantMode.B_CASCADE)
    assert mode == AssistantMode.B_CASCADE
    assert router.active_mode == AssistantMode.B_CASCADE
    assert "Mode B" in msg


def test_model_router_privacy_mode_enforcement(temp_db: Path) -> None:
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    assert router.active_mode == AssistantMode.A_LIVE

    # Enable privacy mode
    msg = router.set_privacy_mode(True)
    assert router.privacy_mode is True
    assert router.active_mode.value == AssistantMode.C_LOCAL.value
    assert "Maxfiylik rejimi" in msg

    # Attempt to switch to Mode A while in Privacy Mode must be rejected
    res_mode, reject_msg = router.set_mode("A")
    assert res_mode == AssistantMode.C_LOCAL
    assert router.active_mode.value == AssistantMode.C_LOCAL.value
    assert "o'tib bo'lmaydi" in reject_msg

    # Disable privacy mode restores previous mode
    router.set_privacy_mode(False)
    assert router.privacy_mode is False
    assert router.active_mode == AssistantMode.A_LIVE


def test_model_router_quota_exhausted_fallback(temp_db: Path) -> None:
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    msg = router.handle_quota_exhausted()
    assert router.active_mode == AssistantMode.C_LOCAL
    assert "kvotasi tugadi" in msg


def test_model_router_network_outage_fallback(temp_db: Path) -> None:
    router = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    msg = router.handle_network_outage()
    assert router.active_mode == AssistantMode.C_LOCAL
    assert "Internet aloqasi uzildi" in msg


def test_model_router_persistence(temp_db: Path) -> None:
    # Instance 1 sets Mode B
    router1 = ModelRouter(initial_mode="A", privacy_mode=False, db_path=temp_db)
    router1.set_mode(AssistantMode.B_CASCADE)

    # Instance 2 reading same DB must load Mode B
    router2 = ModelRouter(db_path=temp_db)
    assert router2.active_mode == AssistantMode.B_CASCADE
