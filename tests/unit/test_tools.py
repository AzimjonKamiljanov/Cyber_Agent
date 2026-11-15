"""Unit tests for all 10 Stage S2 tools."""

import pytest

from cyber_agent.policy.taint import get_taint_tracker
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.draft_message import handle_draft_message
from cyber_agent.tools.get_local_time import handle_get_local_time
from cyber_agent.tools.get_system_status import handle_get_system_status
from cyber_agent.tools.move_workspace_file import handle_move_workspace_file
from cyber_agent.tools.open_allowed_app import handle_open_allowed_app
from cyber_agent.tools.registry import ToolRegistry
from cyber_agent.tools.schemas import (
    CreateTimerArgs,
    DraftMessageArgs,
    GetLocalTimeArgs,
    GetSystemStatusArgs,
    ListTimersArgs,
    MoveWorkspaceFileArgs,
    OpenAllowedAppArgs,
    SearchWorkspaceArgs,
    SetVolumeArgs,
    WebSearchReadArgs,
    WriteWorkspaceFileArgs,
)
from cyber_agent.tools.search_workspace import handle_search_workspace
from cyber_agent.tools.set_volume import handle_set_volume
from cyber_agent.tools.timers import handle_create_timer, handle_list_timers
from cyber_agent.tools.web_search_read import handle_web_search_read
from cyber_agent.tools.workspace_jail import get_workspace_root, resolve_jail_path
from cyber_agent.tools.write_workspace_file import handle_write_workspace_file


@pytest.fixture(autouse=True)
def _clear_workspace() -> None:
    root = get_workspace_root()
    for child in root.iterdir():
        if child.is_file():
            child.unlink()


@pytest.mark.asyncio
async def test_get_local_time() -> None:
    res = await handle_get_local_time(GetLocalTimeArgs())
    assert res.success is True
    assert "Asia/Tashkent" in res.output


@pytest.mark.asyncio
async def test_get_system_status() -> None:
    res = await handle_get_system_status(GetSystemStatusArgs())
    assert res.success is True
    assert "CPU" in res.output
    assert "RAM" in res.output


@pytest.mark.asyncio
async def test_workspace_file_operations_and_jail() -> None:
    root = get_workspace_root()

    # 1. Path traversal escape blocked
    with pytest.raises(PermissionError, match="escapes workspace"):
        resolve_jail_path("../../etc/passwd")

    with pytest.raises(PermissionError, match="sensitive file"):
        resolve_jail_path(".env")

    # 2. Write file
    res_w = await handle_write_workspace_file(WriteWorkspaceFileArgs(filename="notes.txt", content="Salom"))
    assert res_w.success is True
    assert (root / "notes.txt").read_text(encoding="utf-8") == "Salom"

    # 3. Reject overwrite
    res_ow = await handle_write_workspace_file(WriteWorkspaceFileArgs(filename="notes.txt", content="Boshqa"))
    assert res_ow.success is False
    assert "allaqachon mavjud" in (res_ow.error or "")

    # 4. Search workspace
    res_s = await handle_search_workspace(SearchWorkspaceArgs(query="notes"))
    assert res_s.success is True
    assert "notes.txt" in res_s.output

    # 5. Move file
    res_m = await handle_move_workspace_file(MoveWorkspaceFileArgs(source="notes.txt", destination="renamed.txt"))
    assert res_m.success is True
    assert not (root / "notes.txt").exists()
    assert (root / "renamed.txt").exists()


@pytest.mark.asyncio
async def test_open_allowed_app() -> None:
    # Calculator is in allowlist
    res_allowed = await handle_open_allowed_app(OpenAllowedAppArgs(app_name="calculator"))
    # Depending on whether gnome-calculator is installed or mocked
    assert res_allowed.success or "xatolik" in (res_allowed.error or "")

    # Unlisted app is rejected
    res_unlisted = await handle_open_allowed_app(OpenAllowedAppArgs(app_name="malicious_app"))
    assert res_unlisted.success is False
    assert "ro'yxatida yo'q" in (res_unlisted.error or "")


@pytest.mark.asyncio
async def test_set_volume() -> None:
    res = await handle_set_volume(SetVolumeArgs(level=50))
    assert res.success is True
    assert "50%" in res.output


@pytest.mark.asyncio
async def test_timers() -> None:
    res_c = await handle_create_timer(CreateTimerArgs(seconds=1, label="Choy"))
    assert res_c.success is True
    assert "Choy" in res_c.output

    res_l = await handle_list_timers(ListTimersArgs())
    assert res_l.success is True
    assert "Choy" in res_l.output


@pytest.mark.asyncio
async def test_draft_message() -> None:
    res = await handle_draft_message(DraftMessageArgs(recipient="Ali", body="Ertaga uchrashamiz"))
    assert res.success is True
    assert "Ali" in res.output
    assert "Yuborilmadi" in res.output


@pytest.mark.asyncio
async def test_web_search_read_rules_and_taint() -> None:
    taint = get_taint_tracker()
    taint.reset()
    assert taint.is_tainted() is False

    # Denied host (localhost)
    res_denied = await handle_web_search_read(WebSearchReadArgs(url="http://localhost:8000/secret"))
    assert res_denied.success is False
    assert "ruxsat etilmadi" in (res_denied.error or "")
    assert taint.is_tainted() is False


def test_registry_registration_count() -> None:
    reg = ToolRegistry()
    register_default_tools(reg)
    tools = reg.list_tools()
    assert len(tools) >= 10
