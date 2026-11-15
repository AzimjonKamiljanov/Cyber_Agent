"""Unit tests for Playwright browser driver and tools (Stage S4)."""

from pathlib import Path

import pytest

from cyber_agent.policy.taint import SessionTaintTracker
from cyber_agent.tools.browser.driver import BrowserDriver
from cyber_agent.tools.browser.tools import (
    handle_browser_read,
    handle_browser_submit_form,
)
from cyber_agent.tools.browser.url_validator import is_url_allowed
from cyber_agent.tools.schemas import BrowserReadArgs, BrowserSubmitFormArgs


def test_url_validation_rules() -> None:
    """Verify URL allow/deny checks."""
    # Allowed domains
    assert is_url_allowed("https://en.wikipedia.org/wiki/Tashkent")[0] is True
    assert is_url_allowed("https://github.com/AzimjonKamiljanov")[0] is True
    assert is_url_allowed("https://kun.uz/news")[0] is True

    # Denied domains / private networks
    assert is_url_allowed("http://localhost:8000")[0] is False
    assert is_url_allowed("http://127.0.0.1:8080")[0] is False
    assert is_url_allowed("http://192.168.1.100")[0] is False
    assert is_url_allowed("http://10.0.0.1")[0] is False
    assert is_url_allowed("https://device.ts.net")[0] is False

    # Blocked schemes
    assert is_url_allowed("file:///etc/passwd")[0] is False
    assert is_url_allowed("javascript:alert(1)")[0] is False
    assert is_url_allowed("ftp://ftp.example.com")[0] is False


def test_profile_directory_safety(tmp_path: Path) -> None:
    """Ensure driver refuses to point to ~/.config or real browser profiles."""
    home = Path.home()
    driver = BrowserDriver(profile_dir=home / ".config" / "google-chrome")
    with pytest.raises(PermissionError):
        driver._ensure_profile_dir()


@pytest.mark.asyncio
async def test_browser_workflow_with_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test browser open, read with taint tracking, and form submit with local fixture."""
    fixture_html = tmp_path / "test.html"
    fixture_html.write_text(
        """<!DOCTYPE html>
<html>
<head><title>Cyber Test Portal</title></head>
<body>
    <h1>Tizim Boshqaruvi</h1>
    <p>O'zbek tilidagi shaxsiy AI assistent sinov sahifasi.</p>
    <form id="feedback-form" action="/submit" method="POST">
        <input type="text" name="username" id="username" />
        <textarea name="comment" id="comment"></textarea>
        <button type="submit" id="submit-btn">Yuborish</button>
    </form>
</body>
</html>""",
        encoding="utf-8",
    )

    profile_dir = tmp_path / "test_profile"
    driver = BrowserDriver(profile_dir=profile_dir)

    # Monkeypatch global driver to use this isolated test driver
    monkeypatch.setattr("cyber_agent.tools.browser.tools.get_browser_driver", lambda: driver)

    # Test open_url with file fixture allowed
    url = f"file://{fixture_html.resolve()}"
    ok, msg = await driver.open_url(url, allow_file_fixtures=True)
    assert ok is True
    assert "Cyber Test Portal" in msg

    # Test browser_read and taint tracking
    taint_tracker = SessionTaintTracker()
    monkeypatch.setattr("cyber_agent.tools.browser.tools.get_taint_tracker", lambda: taint_tracker)
    assert taint_tracker.is_tainted() is False

    read_res = await handle_browser_read(BrowserReadArgs(max_chars=2000))
    assert read_res.success is True
    assert "Tizim Boshqaruvi" in read_res.output
    assert "O'zbek tilidagi shaxsiy AI assistent" in read_res.output
    assert taint_tracker.is_tainted() is True

    # Test browser_submit_form
    submit_res = await handle_browser_submit_form(
        BrowserSubmitFormArgs(
            form_selector="#feedback-form",
            fields={"username": "Azimjon", "comment": "Ajoyib ishlamoqda"},
        )
    )
    assert submit_res.success is True
    assert "muvaffaqiyatli to'ldirildi" in submit_res.output

    # Clean up
    await driver.close()
