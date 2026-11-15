"""Integration tests for the Kill Switch service, socket protocol, and process group termination."""

import asyncio
import os
import subprocess
import time
from pathlib import Path

import pytest

from cyber_agent.brain.task_queue import TaskQueue, TaskStatus
from cyber_agent.killswitch.client import async_send_command
from cyber_agent.killswitch.process_registry import ProcessRegistry
from cyber_agent.killswitch.service import KillSwitchService
from cyber_agent.policy.confirmations import ConfirmationStore


@pytest.mark.asyncio
async def test_killswitch_subprocess_termination(tmp_path: Path) -> None:
    sock_path = tmp_path / "killswitch.sock"
    db_path = tmp_path / "confirmations.db"

    # Set up isolated service components
    proc_registry = ProcessRegistry()
    confirm_store = ConfirmationStore(db_path=db_path)
    task_queue = TaskQueue()
    task_queue.start()

    service = KillSwitchService(sock_path=sock_path)
    service.process_registry = proc_registry
    service.confirmation_store = confirm_store
    service.task_queue = task_queue

    await service.start()

    try:
        # 1. Spawn a sleeping child process in a NEW process group
        proc = subprocess.Popen(  # noqa: ASYNC220
            ["sleep", "30"],
            start_new_session=True,  # Start new session and process group
        )
        pgid = os.getpgid(proc.pid)
        proc_registry.register_pgid(pgid)

        # 2. Create a pending confirmation
        action_id, _token = confirm_store.create_confirmation("write_workspace_file", {"test": 1})
        conf1 = confirm_store.get_confirmation(action_id)
        assert conf1 is not None and not conf1["consumed"]

        # 3. Enqueue a long task
        async def sleeper() -> None:
            await asyncio.sleep(20)

        task_id = await task_queue.enqueue_task(sleeper, "test sleeper")

        # 4. Trigger STOP via socket client and measure exact time
        t0 = time.monotonic()
        await async_send_command("STOP", sock_path=sock_path)
        elapsed_sec = time.monotonic() - t0

        # Invariant: Must terminate within <= 1.0 second
        assert elapsed_sec < 1.0, f"Killswitch STOP took {elapsed_sec:.4f}s, exceeding 1.0s limit"
        print(f"\n[MEASURED KILL SWITCH LATENCY]: {elapsed_sec * 1000.0:.2f} ms")

        # 5. Assert process group is DEAD
        # wait a tiny moment for OS process table to reap
        poll_start = time.monotonic()
        is_alive = True
        while time.monotonic() - poll_start < 0.5:
            if proc.poll() is not None:
                is_alive = False
                break
            await asyncio.sleep(0.02)

        assert not is_alive, "Subprocess was not killed by kill switch"
        assert proc.returncode is not None

        # 6. Assert confirmation was invalidated
        conf2 = confirm_store.get_confirmation(action_id)
        assert conf2 is not None and conf2["consumed"] is True

        # 7. Assert task queue task was cancelled
        tk = task_queue.get_task(task_id)
        assert tk is not None and tk.status == TaskStatus.CANCELLED

        # 8. Test RESUME
        resume_resp = await async_send_command("RESUME", sock_path=sock_path)
        assert resume_resp["status"] == "IDLE"
        assert service.is_stopped is False

    finally:
        await service.stop()
        await task_queue.stop()
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
