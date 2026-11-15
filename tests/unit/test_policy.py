"""Unit tests for the policy engine, confirmations, and session taint."""

import time
from pathlib import Path

from cyber_agent.policy.confirmations import ConfirmationStore
from cyber_agent.policy.engine import PolicyEngine
from cyber_agent.policy.permissions import PolicyTier, PolicyVerdict
from cyber_agent.policy.taint import SessionTaintTracker


def test_policy_tiers_and_forbidden_tools(tmp_path: Path) -> None:
    store = ConfirmationStore(db_path=tmp_path / "confirm.sqlite3")
    taint = SessionTaintTracker()
    engine = PolicyEngine(confirmation_store=store, taint_tracker=taint)

    engine.register_tool_tier("get_local_time", PolicyTier.GREEN)
    engine.register_tool_tier("write_workspace_file", PolicyTier.YELLOW)

    # 1. Unknown tool -> DENY
    d1 = engine.evaluate("non_existent_tool", {})
    assert d1.verdict == PolicyVerdict.DENY

    # 2. Forbidden RED tool -> DENY
    d2 = engine.evaluate("sudo_command", {"cmd": "id"})
    assert d2.verdict == PolicyVerdict.DENY

    d3 = engine.evaluate("delete_file", {"path": "/etc/passwd"})
    assert d3.verdict == PolicyVerdict.DENY

    # 3. GREEN tool -> ALLOW
    d4 = engine.evaluate("get_local_time", {})
    assert d4.verdict == PolicyVerdict.ALLOW


def test_yellow_tier_confirmation_flow(tmp_path: Path) -> None:
    store = ConfirmationStore(db_path=tmp_path / "confirm.sqlite3")
    taint = SessionTaintTracker()
    engine = PolicyEngine(confirmation_store=store, taint_tracker=taint)

    engine.register_tool_tier("write_workspace_file", PolicyTier.YELLOW)
    args = {"filename": "test.txt", "content": "hello"}

    # 1. First evaluation without token -> returns CONFIRM
    d1 = engine.evaluate("write_workspace_file", args)
    assert d1.verdict == PolicyVerdict.CONFIRM
    assert d1.action_id is not None
    assert d1.confirmation_token is not None

    action_id = d1.action_id
    token = d1.confirmation_token

    # 2. Evaluate with correct action_id and token -> ALLOW
    d2 = engine.evaluate("write_workspace_file", args, action_id=action_id, confirmation_token=token)
    assert d2.verdict == PolicyVerdict.ALLOW

    # 3. Reuse token (already consumed) -> DENY
    d3 = engine.evaluate("write_workspace_file", args, action_id=action_id, confirmation_token=token)
    assert d3.verdict == PolicyVerdict.DENY
    assert "already consumed" in d3.reason


def test_args_tampering_and_expiration(tmp_path: Path) -> None:
    store = ConfirmationStore(db_path=tmp_path / "confirm.sqlite3")
    taint = SessionTaintTracker()
    engine = PolicyEngine(confirmation_store=store, taint_tracker=taint)

    engine.register_tool_tier("write_workspace_file", PolicyTier.YELLOW)
    args = {"filename": "test.txt", "content": "hello"}

    d1 = engine.evaluate("write_workspace_file", args)
    action_id = d1.action_id
    token = d1.confirmation_token

    # Tamper with args
    tampered_args = {"filename": "test.txt", "content": "MALICIOUS PAYLOAD"}
    d_tamper = engine.evaluate("write_workspace_file", tampered_args, action_id=action_id, confirmation_token=token)
    assert d_tamper.verdict == PolicyVerdict.DENY
    assert "tampering detected" in d_tamper.reason

    # Test expiration: create confirmation with short TTL
    act_id_short, token_short = store.create_confirmation("write_workspace_file", args, expiry_seconds=0.01)
    time.sleep(0.02)
    valid, msg = store.validate_and_consume(act_id_short, token_short, args)
    assert valid is False
    assert "expired" in msg


def test_session_taint_tracking(tmp_path: Path) -> None:
    store = ConfirmationStore(db_path=tmp_path / "confirm.sqlite3")
    taint = SessionTaintTracker()
    engine = PolicyEngine(confirmation_store=store, taint_tracker=taint)

    engine.register_tool_tier("write_workspace_file", PolicyTier.YELLOW)

    # Initial state clean
    assert taint.is_tainted() is False

    # Mark tainted by web read
    taint.mark_tainted("https://example.com/untrusted")
    assert taint.is_tainted() is True

    # Evaluation includes taint warning
    d = engine.evaluate("write_workspace_file", {"filename": "a.txt"})
    assert d.verdict == PolicyVerdict.CONFIRM
    assert d.tainted is True
    assert "TAINT WARNING" in d.reason
