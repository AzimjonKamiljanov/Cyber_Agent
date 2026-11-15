"""Unit tests for the Brain Orchestrator and Task Queue."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from cyber_agent.brain.orchestrator import Orchestrator
from cyber_agent.brain.task_queue import TaskQueue, TaskStatus
from cyber_agent.policy.confirmations import ConfirmationStore
from cyber_agent.policy.engine import PolicyEngine
from cyber_agent.policy.taint import SessionTaintTracker
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.registry import ToolRegistry


@pytest.fixture
async def test_setup(
    tmp_path: Path,
) -> AsyncIterator[tuple[Orchestrator, ConfirmationStore, SessionTaintTracker, TaskQueue]]:
    db_path = tmp_path / "confirmations.db"
    store = ConfirmationStore(db_path=db_path)
    engine = PolicyEngine(confirmation_store=store)
    taint = SessionTaintTracker()
    registry = ToolRegistry(policy_engine=engine)
    register_default_tools(registry)
    queue = TaskQueue()
    queue.start()

    orchestrator = Orchestrator(
        tool_registry=registry,
        policy_engine=engine,
        confirmation_store=store,
        taint_tracker=taint,
        task_queue=queue,
    )
    yield orchestrator, store, taint, queue
    await queue.stop()


@pytest.mark.asyncio
async def test_orchestrator_green_tool(test_setup: Any) -> None:
    orchestrator, _, _, _ = test_setup
    resp = await orchestrator.handle_tool_call(
        name="get_local_time",
        args={"timezone": "Asia/Tashkent"},
    )
    assert resp.status == "success"
    assert "Hozirgi vaqt" in resp.spoken_message


@pytest.mark.asyncio
async def test_orchestrator_forbidden_tool(test_setup: Any) -> None:
    orchestrator, _, _, _ = test_setup
    resp = await orchestrator.handle_tool_call(
        name="arbitrary_shell",
        args={"cmd": "ls"},
    )
    assert resp.status == "denied"
    assert "rad etildi" in resp.spoken_message


@pytest.mark.asyncio
async def test_orchestrator_yellow_confirmation_flow(
    test_setup: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CYBER_WORKSPACE_DIR", str(tmp_path))
    from cyber_agent.config import get_settings

    get_settings.cache_clear()
    orchestrator, _store, _, _ = test_setup

    # 1. First call without token -> confirm_required
    resp1 = await orchestrator.handle_tool_call(
        name="write_workspace_file",
        args={"filename": "test.txt", "content": "Hello World"},
    )
    assert resp1.status == "confirm_required"
    assert resp1.confirmation_card is not None
    action_id = resp1.confirmation_card["action_id"]
    token = resp1.confirmation_card["token"]

    # 2. Second call with valid token -> success
    resp2 = await orchestrator.handle_tool_call(
        name="write_workspace_file",
        args={"filename": "test.txt", "content": "Hello World"},
        action_id=action_id,
        confirmation_token=token,
    )
    assert resp2.status == "success"
    assert (tmp_path / "test.txt").exists()


@pytest.mark.asyncio
async def test_orchestrator_long_running_tool(test_setup: Any) -> None:
    orchestrator, _, _, _ = test_setup
    # run_test_suite is YELLOW, so it requires confirmation first
    resp1 = await orchestrator.handle_tool_call(
        name="run_test_suite",
        args={"test_path": "tests/unit/test_config.py"},
    )
    assert resp1.status == "confirm_required"
    action_id = resp1.confirmation_card["action_id"]
    token = resp1.confirmation_card["token"]

    # With confirmation, it gets enqueued
    resp2 = await orchestrator.handle_tool_call(
        name="run_test_suite",
        args={"test_path": "tests/unit/test_config.py"},
        action_id=action_id,
        confirmation_token=token,
    )
    assert resp2.status == "enqueued"
    assert "fonda" in resp2.spoken_message
    assert "task_id" in resp2.data


@pytest.mark.asyncio
async def test_task_queue_cancellation() -> None:
    queue = TaskQueue()
    queue.start()

    async def long_sleep() -> str:
        await asyncio.sleep(10.0)
        return "done"

    task_id = await queue.enqueue_task(long_sleep, "Sleeping task")
    assert len(queue.list_active()) == 1

    cancelled = queue.cancel_all()
    assert cancelled >= 1
    task = queue.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.CANCELLED
    await queue.stop()
