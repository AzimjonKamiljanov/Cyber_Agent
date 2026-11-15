"""Unit tests for Bubblewrap Sandbox Executor and command allowlist (Stage S4)."""

from pathlib import Path

import pytest

from cyber_agent.killswitch.process_registry import get_process_registry
from cyber_agent.sandbox.executor import SandboxExecutor, is_command_allowed
from cyber_agent.tools.run_allowed_command import handle_run_allowed_command
from cyber_agent.tools.schemas import RunAllowedCommandArgs


def test_command_allowlist_validation(tmp_path: Path) -> None:
    """Test allowlist prefix rules and security rejections."""
    # Allowed commands
    assert is_command_allowed(["git", "status"])[0] is True
    assert is_command_allowed(["git", "status", "--short"])[0] is True
    assert is_command_allowed(["ls"])[0] is True
    assert is_command_allowed(["ls", "-l"])[0] is True
    assert is_command_allowed(["pwd"])[0] is True

    # Unlisted commands
    assert is_command_allowed(["rm", "-rf", "data"])[0] is False
    assert is_command_allowed(["curl", "https://google.com"])[0] is False
    assert is_command_allowed(["bash", "-c", "whoami"])[0] is False
    assert is_command_allowed(["git", "commit", "-m", "bad"])[0] is False

    # Path spoofing (cannot run binaries with path separators)
    assert is_command_allowed(["./git", "status"])[0] is False
    assert is_command_allowed(["/bin/ls"])[0] is False
    assert is_command_allowed(["/tmp/evil_bin"])[0] is False

    # Path traversal / escape in arguments
    assert is_command_allowed(["ls", "../../../.ssh"])[0] is False
    assert is_command_allowed(["ls", "..\\..\\sensitive"])[0] is False

    # Secrets access in arguments
    assert is_command_allowed(["ls", ".env"])[0] is False
    assert is_command_allowed(["ls", "id_rsa"])[0] is False

    # Shell operators in arguments
    assert is_command_allowed(["git", "status", ";", "rm"])[0] is False
    assert is_command_allowed(["ls", "|", "grep", "foo"])[0] is False
    assert is_command_allowed(["ls", "$HOME"])[0] is False


@pytest.mark.asyncio
async def test_sandbox_execution_and_env_sanitization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify command runs in sandbox without leaking environment secrets."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()

    # Inject dummy secret in host env
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET_KEY_12345")
    monkeypatch.setenv("MY_PRIVATE_TOKEN", "TOP_SECRET_ABC")

    executor = SandboxExecutor(workspace_dir=workspace)

    # Run safe 'pwd' command
    code, stdout, _stderr = await executor.run(["pwd"])
    assert code == 0
    assert str(workspace) in stdout

    # Verify sanitized env does NOT contain host secrets
    env = executor._build_sanitized_env()
    assert "GEMINI_API_KEY" not in env
    assert "MY_PRIVATE_TOKEN" not in env


@pytest.mark.asyncio
async def test_run_allowed_command_handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tool handler for run_allowed_command."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    executor = SandboxExecutor(workspace_dir=workspace)
    monkeypatch.setattr("cyber_agent.tools.run_allowed_command.get_sandbox_executor", lambda: executor)

    # Valid allowed command
    res_ok = await handle_run_allowed_command(RunAllowedCommandArgs(argv=["pwd"]))
    assert res_ok.success is True
    assert str(workspace) in res_ok.output

    # Forbidden command
    res_deny = await handle_run_allowed_command(RunAllowedCommandArgs(argv=["rm", "-rf", "/"]))
    assert res_deny.success is False
    assert res_deny.error is not None and "rad etildi" in res_deny.error


@pytest.mark.asyncio
async def test_sandbox_kill_switch_process_tracking(tmp_path: Path) -> None:
    """Ensure process groups are registered and cleaned up."""
    registry = get_process_registry()
    initial_pgids = len(registry.list_pgids())

    workspace = tmp_path / "ws_proc"
    workspace.mkdir()
    executor = SandboxExecutor(workspace_dir=workspace)

    code, _, _ = await executor.run(["pwd"])
    assert code == 0

    # Cleaned up after execution
    assert len(registry.list_pgids()) == initial_pgids
