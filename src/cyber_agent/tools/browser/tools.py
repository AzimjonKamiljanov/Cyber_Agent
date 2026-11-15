"""Browser interaction tools for Cyber Agent Stage S4.

Implements:
- browser_open (GREEN)
- browser_read (GREEN, marks session tainted)
- browser_submit_form (YELLOW, requires user confirmation)
"""

from __future__ import annotations

import logging
from typing import Any

from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.policy.taint import get_taint_tracker
from cyber_agent.tools.browser.driver import get_browser_driver
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry
from cyber_agent.tools.schemas import (
    BrowserOpenArgs,
    BrowserReadArgs,
    BrowserSubmitFormArgs,
    ToolResult,
)

logger = logging.getLogger(__name__)


async def handle_browser_open(args: Any) -> ToolResult:
    """Open a URL in the isolated Playwright browser."""
    driver = get_browser_driver()
    url = getattr(args, "url", "")
    ok, msg = await driver.open_url(url)
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


async def handle_browser_read(args: Any) -> ToolResult:
    """Read the current page content and mark session tainted."""
    driver = get_browser_driver()
    max_chars = getattr(args, "max_chars", 4000)
    ok, content, url = await driver.read_content(max_chars=max_chars)
    if not ok:
        return ToolResult(success=False, output="", error=content)

    # Invariant: External web content TAINTs the session
    tracker = get_taint_tracker()
    tracker.mark_tainted(source=url or "browser_page")

    return ToolResult(
        success=True,
        output=f"Brauzer sahifasi mazmuni ({url}) [SESSIYA ZARARLANDI]:\n{content}",
    )


async def handle_browser_submit_form(args: Any) -> ToolResult:
    """Submit a form in the current page (YELLOW tier)."""
    driver = get_browser_driver()
    form_selector = getattr(args, "form_selector", "")
    fields = getattr(args, "fields", {})

    ok, msg = await driver.submit_form(form_selector=form_selector, fields=fields)
    if ok:
        return ToolResult(success=True, output=msg)
    return ToolResult(success=False, output="", error=msg)


def register_browser_tools(registry: ToolRegistry) -> None:
    """Register Playwright browser automation tools."""
    registry.register(
        ToolDefinition(
            name="browser_open",
            description="Alohidalanlangan Playwright profilida ruxsat etilgan URL manzilini ochadi.",
            tier=PolicyTier.GREEN,
            args_schema=BrowserOpenArgs,
            handler=handle_browser_open,
        )
    )
    registry.register(
        ToolDefinition(
            name="browser_read",
            description="Brauzerdagi faol sahifaning matnini o'qiydi (Sessiya xavfsizlik maqsadida zararlangan deb belgilanadi).",
            tier=PolicyTier.GREEN,
            args_schema=BrowserReadArgs,
            handler=handle_browser_read,
        )
    )
    registry.register(
        ToolDefinition(
            name="browser_submit_form",
            description="Brauzer sahifasidagi ko'rsatilgan forma maydonlarini to'ldiradi va yuboradi (YELLOW tier).",
            tier=PolicyTier.YELLOW,
            args_schema=BrowserSubmitFormArgs,
            handler=handle_browser_submit_form,
        )
    )
