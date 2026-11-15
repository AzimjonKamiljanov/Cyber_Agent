"""Unit tests for desktop automation tools and safety invariants (Stage S4)."""

import json
from pathlib import Path

import pytest

from cyber_agent.tools.desktop.backend import DesktopDriver, WindowInfo
from cyber_agent.tools.desktop.tools import (
    handle_gui_click,
    handle_gui_type,
    handle_read_ui_tree,
    handle_window_focus,
    handle_window_list,
)
from cyber_agent.tools.schemas import (
    GUIClickArgs,
    GUITypeArgs,
    ReadUITreeArgs,
    WindowFocusArgs,
    WindowListArgs,
)


@pytest.fixture
def mock_desktop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> DesktopDriver:
    """Fixture providing a DesktopDriver with predefined windows and config."""
    config_file = tmp_path / "sensitive_windows.toml"
    config_file.write_text(
        """[denylist]
titles = ["*1Password*", "*Bitwarden*", "*KeePassXC*", "*banking*", "secret*"]
app_classes = ["1password", "bitwarden", "keepassxc"]
""",
        encoding="utf-8",
    )
    driver = DesktopDriver(config_path=config_file)
    driver._mock_windows = [
        WindowInfo("win-01", "Ghostty Terminal", "com.mitchellh.ghostty", "primary", False),
        WindowInfo("win-02", "Firefox Browser", "firefox", "secondary", False),
        WindowInfo("win-03", "1Password Vault", "1password", "primary", True),
    ]
    monkeypatch.setattr("cyber_agent.tools.desktop.tools.get_desktop_driver", lambda: driver)
    return driver


@pytest.mark.asyncio
async def test_window_list_masks_sensitive_windows(mock_desktop: DesktopDriver) -> None:
    """Ensure sensitive windows are masked unless specifically requested."""
    res = await handle_window_list(WindowListArgs(include_sensitive=False))
    assert res.success is True
    data = json.loads(res.output)
    assert len(data) == 3

    # win-03 is sensitive -> masked title
    assert data[2]["title"] == "[MAXFIY OYNA]"
    assert data[2]["is_sensitive"] is True

    # With include_sensitive=True
    res_incl = await handle_window_list(WindowListArgs(include_sensitive=True))
    data_incl = json.loads(res_incl.output)
    assert data_incl[2]["title"] == "1Password Vault"


@pytest.mark.asyncio
async def test_window_focus(mock_desktop: DesktopDriver) -> None:
    """Test focusing open windows and handling non-existent targets."""
    ok_res = await handle_window_focus(WindowFocusArgs(target="Ghostty"))
    assert ok_res.success is True
    assert "fokus o'rnatildi" in ok_res.output

    fail_res = await handle_window_focus(WindowFocusArgs(target="NonExistentApp"))
    assert fail_res.success is False
    assert fail_res.error is not None and "topilmadi" in fail_res.error


@pytest.mark.asyncio
async def test_read_ui_tree(mock_desktop: DesktopDriver) -> None:
    """Test reading semantic UI hierarchy."""
    res = await handle_read_ui_tree(ReadUITreeArgs(window_title="Ghostty Terminal", max_depth=2))
    assert res.success is True
    data = json.loads(res.output)
    assert data["name"] == "Ghostty Terminal"
    assert "children" in data
    assert len(data["children"]) > 0


@pytest.mark.asyncio
async def test_gui_click_boundaries_and_sensitive_checks(mock_desktop: DesktopDriver) -> None:
    """Verify click coordinates and refusal on sensitive windows."""
    # Valid click on primary (scale 1.33: 1920x1200)
    res_valid = await handle_gui_click(GUIClickArgs(x=500, y=300, monitor="primary"))
    assert res_valid.success is True

    # Out of bounds click
    res_oob = await handle_gui_click(GUIClickArgs(x=3000, y=400, monitor="primary"))
    assert res_oob.success is False
    assert res_oob.error is not None and "xato" in res_oob.error

    # Click on sensitive window
    res_sens = await handle_gui_click(
        GUIClickArgs(x=100, y=100, monitor="primary", target_window="1Password Vault")
    )
    assert res_sens.success is False
    assert res_sens.error is not None and "maxfiy oynalar ro'yxatida" in res_sens.error


@pytest.mark.asyncio
async def test_gui_type_password_and_sensitive_refusal(mock_desktop: DesktopDriver) -> None:
    """Security Invariant: Never type into password fields or sensitive windows."""
    # Refuse password element
    res_pwd = await handle_gui_type(
        GUITypeArgs(
            text="secretpassword123",
            target_window="Firefox Browser",
            target_element_role="password text",
            target_element_name="Parol kiriting",
        )
    )
    assert res_pwd.success is False
    assert res_pwd.error is not None and "Parol yoki maxfiy maydonlarga" in res_pwd.error

    # Refuse sensitive window
    res_sens = await handle_gui_type(
        GUITypeArgs(
            text="my text",
            target_window="1Password Vault",
            target_element_role="entry",
            target_element_name="Search",
        )
    )
    assert res_sens.success is False
    assert res_sens.error is not None and "maxfiy oynasida matn kiritish taqiqlangan" in res_sens.error

    # Normal typing into safe window succeeds
    res_ok = await handle_gui_type(
        GUITypeArgs(
            text="ls -la",
            target_window="Ghostty Terminal",
            target_element_role="terminal",
            target_element_name="prompt",
        )
    )
    assert res_ok.success is True
